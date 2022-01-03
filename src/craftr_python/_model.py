
import dataclasses


@dataclasses.dataclass
class Author:
  name: str
  email: str

  def to_json(self) -> dict[str, str]:
    return {'name': self.name, 'email': self.email}
