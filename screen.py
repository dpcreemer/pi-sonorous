import sys, mmap
from PIL import Image, ImageDraw, ImageFont
from evdev import InputDevice, ecodes


FB_DEVICE = "/dev/fb0"

#Quick function to read data from a file
def _read(path):
  with open(path, "r") as f:
    return f.read().strip()

class Color:
  white = (255, 255, 255, 255)
  black = (0, 0, 0, 255)
  light_grey = (240, 240, 240, 255)
  yellow = (230, 230, 90, 255)
  blue = (90, 170, 230, 255)
  dark_blue = (12, 32, 44, 255)

class Button(object):
  def __init__(self, label, x, y, width, height, font, color=Color.black, background_color=Color.blue):
    self.label = label
    self.x = x
    self.y = y
    self.width = width
    self.height = height
    self.font = font
    self.color = color
    self.background_color = background_color

  def point_in_button(self, px, py): 
    rv = self.x < px < self.x + self.width
    rv &= self.y < py < self.y + self.height
    return rv


class Screen(object):
  def __init__(self, 
               fb_device = "/dev/fb0", 
               touch_device = "/dev/input/touchscreen", 
               touch_calibration = "/etc/pointercal"):
    self.fb_device = fb_device
    self.touch_device = touch_device
    fb = fb_device.split("/")[-1]
    width, height = map(int, _read(f"/sys/class/graphics/{fb}/virtual_size").split(","))
    self.width = width
    self.height = height
    bits_per_pixel = int(_read(f"/sys/class/graphics/{fb}/bits_per_pixel"))
    self.framebuffer_size = width * height * bits_per_pixel // 8
    self.pointer_calibration = self.load_pointer_calibration(touch_calibration)
    self.canvas = Image.new("RGBA", (self.width, self.height), Color.black)  # background
    self.draw = ImageDraw.Draw(self.canvas)
    self.hide_cursor()

  def open_touch_device(self):
    return InputDevice(self.touch_device)

  def load_pointer_calibration(self, calibration):
    with open(calibration) as f:
      vals = [int(v) for v in f.read().split()][:7]
    if len(vals) != 7:
      raise ValueError("pointercal must have 7 integers")
    return vals
  
  def apply_pointer_calibration(self, x_raw, y_raw):
    if self.pointer_calibration:
      c1, c2, c3, c4, c5, c6, c7 = self.pointer_calibration
      x = (c1 * x_raw + c2 * y_raw + c3) / c7
      y = (c4 * x_raw + c5 * y_raw + c6) / c7
    else:
      x, y = x_raw, y_raw
    return int(x), int(y)
  
  # check for touch anhd return ((x, y), last_x, last_y) on finger up
  # else return (None, last_x, last_y)
  def poll_touch_up(self, device, last_x, last_y):
    event = device.read_one()
    touch_up_pos = None

    while event is not None:
      if event.type == ecodes.EV_ABS:
        if event.code == ecodes.ABS_X:
          last_x = event.value
        elif event.code == ecodes.ABS_Y:
          last_y = event.value
      elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH and event.value == 0:   # finger up
        touch_up_pos = self.apply_pointer_calibration(last_x, last_y)

      event = device.read_one()

    return touch_up_pos, last_x, last_y 

  def write(self, img=None):
    if img is None:
      img = self.canvas
    if img.size != (self.width, self.height):
      img = img.resize((self.width, self.height), image.BILINEAR)
    if img.mode != "RGBA":
      img = img.convert("RGBA")
    
    raw = img.tobytes("raw", "BGRA")

    with open(self.fb_device, "r+b", buffering=0) as fb:
      mm = mmap.mmap(fb.fileno(), self.framebuffer_size, mmap.MAP_SHARED, mmap.PROT_WRITE)
      mm.seek(0)
      mm.write(raw)
      mm.flush()
      mm.close()
  
  def close(self):
    temp_canvas = Image.new("RGBA", (self.width, self.height), Color.blue)
    self.write(temp_canvas)
    with open("/dev/tty1", "w") as tty:
      tty.write("\033[2J\033[H\033[?25h") # clear, home, show cursor
  
  def hide_cursor(self):
    with open("/dev/tty1", "w") as tty:
      tty.write("\033[?25l")  # hide cursor
  
  def show_cursor(self):
    with open("/dev/tty1", "w") as tty:
      tty.write("\033[?25h")  # show cursor
  
  def text_size(self, text, font):
    bbox = self.draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

  def wrap_text(self, text, font, max_width=0):
    if max_width == 0:
      max_width = self.width - 20
    output_text = ""
    for word in text.split():
      w, _ = self.text_size(f"{output_text} {word}", font)
      if w <= max_width:
        output_text += " " + word
      else:
        output_text += "\n" + word
    return output_text

  def draw_text(self, text, x=-1, y=-1, center_x=-1, center_y=-1, color=Color.white, font=ImageFont.load_default()):
    text = self.wrap_text(text, font)
    if center_x != -1 or center_y != -1:
      text_width, text_height = self.text_size(text, font)
      if center_x != -1:
        x = center_x - (text_width // 2)
      if center_y != -1:
        y = center_y - (text_height // 2)
    self.draw.text((x, y), text, fill=color, font=font, align="center")
  
  def draw_image(self, image, width, height, x=0, y=0, center_x=0, center_y=0, rotate=0):
    if rotate:
      image = image.rotate(rotate, expand=True)
    image.thumbnail((width, height), Image.BILINEAR)
    if center_x: 
      x = center_x - (image.width // 2)
    if center_y:
      y = center_y - (image.height // 2)
    self.draw.rectangle([x-2, y-2, x+image.width+1, y+image.height+1], fill=Color.black, outline=Color.yellow, width=2)
    self.canvas.paste(image, (x, y))

  def show_button(self, button):
    self.draw.rounded_rectangle([button.x, button.y, button.x + button.width, button.y + button.height],
                                radius = 16,
                                fill = button.background_color)
    self.draw_text(button.label, 
                   center_x=button.x+(button.width//2), 
                   center_y=button.y+(button.height//2)-5,
                   color=button.color,
                   font=button.font)