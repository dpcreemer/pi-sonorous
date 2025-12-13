import soco  #Open source Sonos managment library

# Return a set of speakers on the local network
def get_speakers() -> set[soco.core.SoCo]:
  return soco.discover(allow_network_scan=True) or set()

# Get a list of speaker names
def get_speaker_names() -> list[str]:
  return [speaker.player_name for speaker in get_speakers()]

# Find a speaker by name
def get_speaker_by_name(name: str) -> soco.core.SoCo | None: 
  speakers = get_speakers()
  for speaker in speakers:
    if name.lower() == speaker.player_name.lower():
      return speaker
  return None

######################################
# A simple object to manage a sonos speaker.  
# Initialized with a speaker name or by passing a soco.core.SoCo object
class Speaker(object):
  def __init__(self, speaker):
    self.speaker = speaker

  def __repr__(self):
    return self.name

  # The soco.core.SoCo object used to manage the speaker
  @property
  def speaker(self) -> soco.core.SoCo:
    return self._speaker
  
  # Set the local speaker attribute to a soco.core.Soco object.
  # expects a name as a string or a soco.core.Soco object.
  # sets to None type if no match is made.
  @speaker.setter
  def speaker(self, speaker: str | soco.core.SoCo):
    if isinstance(speaker, soco.core.SoCo):
      self._speaker = speaker
    elif type(speaker) is str:
      self._speaker = get_speaker_by_name(speaker)
    else:
      self._speaker = None
    if self._speaker is None: 
      raise ValueError("Speaker not found!")

  # Get the name of the speaker
  @property
  def name(self) -> str:
    return self.speaker.player_name

  # Get the current state of the speaker: PLAYING, PAUSED, STOPPED, etc.
  @property
  def state(self) -> str:
    state = self._speaker.get_current_transport_info()["current_transport_state"]
    if state == "PAUSED_PLAYBACK":
      return "PAUSED"
    return state

  # Change the current state of the speaker (case insensitive)
  @state.setter
  def state(self, state: str):
    if state.lower() in ["play", "playing"]:
      self.speaker.play()
    elif state.lower() in ["pause", "paused"]:
      self.speaker.pause()
    elif state.lower() in ["stop", "stopped"]:
      self.speaker.stop()
    else:
      raise ValueError(f"Unknown state \"{state}\"")

  # Get Track, Artist, and Album of the current track
  @property
  def track_info(self) -> dict:
    return self.__get_track_info()

  # Get the artist currently being played
  @property
  def artist(self) -> str:
    return self.track_info["artist"]

  # Get the track currently being played
  @property
  def track(self) -> str:
    return self.track_info["track"]

  # Get the album currently playing
  @property
  def album(self) -> str:
    return self.track_info["album"]

  # Get the volume setting
  @property
  def volume(self) -> int:
    return self.speaker.volume

  # Set the volume 
  @volume.setter
  def volume(self, value: int):
    self.speaker.volume = value

  # Get the mute setting
  @property
  def mute(self) -> bool:
    return self.speaker.mute
  
  # Set the mute setting
  @mute.setter
  def mute(self, value: bool):
    self.speaker.mute = value

  # Read the current track info from the speaker
  def __get_track_info(self) -> dict:
    track_data = self.speaker.group.coordinator.get_current_track_info()
    track = track_data["title"]
    artist = track_data["artist"]
    album = track_data["album"]
    if not artist and "-" in track:
      track, artist = track.split("-", 1)
    return {
      "track": track.strip(),
      "artist": artist.strip(),
      "album": album.strip()
    }
  
  # Change the state to Playing
  def play(self):
    self.speaker.play()
  
  # Change the state to Paused
  def pause(self):
    self.speaker.pause()

  # Stop playback.
  def stop(self):
    self.speaker.stop()


