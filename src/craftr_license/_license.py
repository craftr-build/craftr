import datetime
import typing as t

from pkg_resources import resource_string

from craftr.bld.renderers import FileRendererTask
from craftr.core import ActionContext, PathProperty, Property
from craftr.utils.fs import get_file_in_directory

from ._dejacode import get_license_metadata, wrap_license_text

# https://spdx.org/licenses/
LICENSE_TEMPLATE_MAP = {
  'MIT.txt': ['MIT'],
  'BSD2.txt': ['BSD-2-Clause', 'BSD-Simplified', 'BSD-2', 'BSD2'],
  'BSD3.txt': ['BSD-3-Clause', 'BSD-new', 'BSD-3', 'BSD3'],
  'BSD4.txt': ['BSD-4-Clause', 'BSD-old', 'BSD-Original'],
  'Apache2.txt': ['Apache-2.0', 'Apache-2', 'Apache2']
}


class LicenseTemplateDoesNotExist(Exception):
  pass


def get_license_template(license_name: str) -> str:
  for license_filename, license_identifiers in LICENSE_TEMPLATE_MAP.items():
    for license_identifier in license_identifiers:
      if license_name.lower() == license_identifier.lower():
        # NOTE (NiklasRosenstein): See https://github.com/NiklasRosenstein/shut/issues/17
        return resource_string(__name__, f'license_templates/{license_filename}').decode('utf-8')
  raise LicenseTemplateDoesNotExist('License template not available for supplied license name', license_name)


class RenderLicenseTask(FileRendererTask):
  """
  Renders a `LICENSE` file into the project root directory.
  """

  output_file = PathProperty.output()
  id: Property[str]
  author: Property[str]

  def finalize(self) -> None:
    super().finalize()
    if not self.output_file.is_set():
      license_file = get_file_in_directory(
        directory=str(self.project.directory),
        prefix='LICENSE.',
        preferred=['LICENSE', 'LICENSE.txt'],
        case_sensitive=False,
      ) or 'LICENSE'
      self.output_file.set(license_file)
    if not self.id.is_set():
      self.enabled = False

  def get_file_contents(self) -> str:
    return get_license_template(self.id.get()).format(
      year=datetime.datetime.utcnow().year,
      author=self.author.get(''),
    )

  def __call__(self, arg=None):
    if isinstance(arg, str):
      self.id.set(arg)
      arg = None
    if arg is not None:
      super().__call__(arg)
