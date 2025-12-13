from requests import Session   # Used to make API calls to internet sources
from PIL import Image          # Used to manage image data for cover art
from io import BytesIO         # Used for converting data to/from byte format

HEADER_AGENT=headers = "Pecan/1.0 (davis@creemer.net)"      # Header to identify my app to musicbrainz

# Retrieve a unique Release Group ID for a specific artist and album
# Data comes from musicbrainz.org.  First match on artist and album is accepted.
# musicbrainz.org searches are not case sensitive
def find_album_release_group(artist: str, album: str) -> str | None:
  session = Session()
  headers = {"User-Agent": HEADER_AGENT}
  params = {
    "query": f'release:"{album}" AND artist:"{artist}"', 
    "fmt": "json"
  }
  
  response = session.get("https://musicbrainz.org/ws/2/release", headers=headers, params=params)
  if not response.ok or response.json()['count'] == 0:
    return None
  
  return response.json()["releases"][0]["release-group"]["id"]

# Retrieve a unique Release Group ID for a specific artist and track
# Data comes from musicbrainz.org catalog of "recordings"
# filter to release-groups of type "Album"
# release-groups with a "secondary-type" are ignored as these usualy aren't the main album
def find_track_release_group(artist: str, track:str) -> str | None:
  session = Session()
  headers = {"User-Agent": HEADER_AGENT}
  params = {
    "query": f'recording:"{track}" AND artist:"{artist}"', 
    "fmt": "json"
  }
  
  response = session.get("https://musicbrainz.org/ws/2/recording", headers=headers, params=params)
  if not response.ok:
    return None
  
  release_groups = []
  for recording in response.json()["recordings"]:
    if "releases" in recording.keys():
      for release in recording["releases"]:
        release_group = release["release-group"]
        if "primary-type" in release_group and "secondary-types" not in release_group:
          if release_group["primary-type"] == "Album":
            release_groups.append(release_group["id"])
  
  if release_groups: 
    return release_groups[0]
  return None

# get album art from coverartarchive.org 
# requires a release group for input
def get_album_art_by_release_group(release_group: str):
  session = Session()
  response = session.get(f"https://coverartarchive.org/release-group/{release_group}/front-250")
  if not response.ok:
    return None
  image = Image.open(BytesIO(response.content)).convert("RGB")
  return image

# Get album art from coverartarchive.org.  
# Search based on Artist and (album or track)
# Return None if album art isn't found.
def get_album_art(artist : str, album : str = "", track : str = ""):
  if not (album or track):
    raise ValueError("Either album or track title must be provided.")
  if album:
    release_group = find_album_release_group(artist, album)
  else:
    release_group = find_track_release_group(artist, track)
  
  image = None
  if release_group:
    image = get_album_art_by_release_group(release_group)
  
  if not (release_group and image):
    image = Image.open("images/music.png").convert("RGBA")
  return image