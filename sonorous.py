
from screen import Screen, Button, Color
import sonos
import music_info
from PIL import ImageFont
from evdev import ecodes
import time

POLL_INTERVAL = 2    # delay between sonos track info queries
LOOP_SLEEP = 0.05    # base loop delay
FONT_STD = ImageFont.truetype("fonts/DejaVuSans.ttf", 22)
FONT_BIG  = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 22)


def show_now_playing(screen, artist, track):
  print(f"Now playing: \"{track}\" by \"{artist}\"")
  image = music_info.get_album_art(artist=artist, track=track)
  screen.draw_image(image, 220, 220, center_x=screen.width//2, center_y=160)

  screen.draw.rectangle([0,285, screen.width, 400], fill=Color.black)
  screen.draw_text(track, center_x=screen.width//2, y=290, color=Color.light_grey, font=FONT_BIG)
  screen.draw_text(artist, center_x=screen.width//2, y=345, color=Color.blue, font=FONT_STD)
  
  screen.write()

def handle_play_button(button_play, screen, speaker):
  if speaker.state != "PLAYING":
    speaker.play()
    button_play.label = "Pause"
  else:
    speaker.pause()
    button_play.label = "Play"
  screen.show_button(button_play)
  screen.write()

def handle_mute_button(button_mute, screen, speaker):
  speaker.mute = not speaker.mute
  button_mute.label = "Unmute" if speaker.mute else "Mute"
  screen.show_button(button_mute)
  screen.write()

def track_info_screen(speaker):
  print(f"showing track info for {speaker.name}")
  screen = Screen()

  screen.draw_text(speaker.name, x=0, y=0, font=FONT_STD)

  artist = speaker.artist
  track = speaker.track
  show_now_playing(screen, artist, track)

  button_close = Button("X", 295, 5, 20, 20, FONT_STD, color=Color.blue, background_color=Color.black)
  button_play = Button("Pause", 20, 410, 120, 50, FONT_STD)
  button_mute = Button("Mute", 180, 410, 120, 50, FONT_STD)

  screen.show_button(button_play)
  screen.show_button(button_close)
  screen.show_button(button_mute)

  screen.write()

  # After drawing and fb_write(img)
  dev = screen.open_touch_device()
  last_x, last_y = (0, 0)

  last_poll = time.monotonic()
  running = True

  while running:
    time.sleep(LOOP_SLEEP)
    touch, last_x, last_y = screen.poll_touch_up(dev, last_x, last_y)
    if touch:
      sx, sy = touch
      if button_play.point_in_button(sx, sy):
        handle_play_button(button_play, screen, speaker)
      elif button_mute.point_in_button(sx, sy):
        handle_mute_button(button_mute, screen, speaker)
      elif button_close.point_in_button(sx, sy):
        running = False

    if time.monotonic() - last_poll >= POLL_INTERVAL:
      last_poll = time.monotonic()
      current_artist = speaker.artist
      current_track = speaker.track
      
      if (current_artist != artist) or (current_track != track):
        artist = current_artist
        track = current_track
        show_now_playing(screen, artist, track)

  screen.close()

def choose_speaker():
  screen = Screen()
  buttons = []
  button_y = 40
  button_close = Button("X", 295, 5, 20, 20, FONT_STD, color=Color.blue, background_color=Color.black)
  screen.show_button(button_close)
  for speaker in sonos.get_speaker_names():
    button = Button(speaker, 40, button_y, screen.width-80, 50, FONT_STD)
    screen.show_button(button)
    buttons.append(button)
    button_y += 70
  screen.write()
  dev = screen.open_touch_device()
  last_x, last_y = (0, 0)
  running = True

  while running:
    time.sleep(LOOP_SLEEP)
    touch, last_x, last_y = screen.poll_touch_up(dev, last_x, last_y)
    if touch:
      sx, sy = touch
      if button_close.point_in_button(sx, sy):
        return None
      for button in buttons:
        if button.point_in_button(sx, sy):
          return button.label
  
def main():
  print("Staring app")
  running = True
  while running:
    speaker_name = choose_speaker()
    if speaker_name:
      track_info_screen(sonos.Speaker(speaker_name))
    else:
      running = False
  
  Screen().close()


if __name__ == "__main__":
  main()