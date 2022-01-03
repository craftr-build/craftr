from craftr.core import ExtensionRegistry, Project

from ._license import RenderLicenseTask


def registry(project: Project) -> None:
  project.task('license', RenderLicenseTask)
