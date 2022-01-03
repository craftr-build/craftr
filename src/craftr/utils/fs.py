import os
import typing as t


def get_file_in_directory(
  directory: str,
  prefix: str,
  preferred: t.List[str],
  case_sensitive: bool = True,
) -> t.Optional[str]:
  """
  Returns a file in *directory* that is either in the *preferred* list or starts with
  specified *prefix*.
  """

  if not case_sensitive:
    preferred = [x.lower() for x in preferred]

  choices = []
  for name in sorted(os.listdir(directory)):
    if (case_sensitive and name in preferred) or (not case_sensitive and name.lower() in preferred):
      return os.path.join(directory, name)
    if name.startswith(prefix):
      choices.append(name)
  else:
    if choices:
      return choices[0]

  return None
