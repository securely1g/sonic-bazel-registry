from typing import Any
from jinja2 import Template, Environment, FileSystemLoader
from .sai_file_updater import SAIFileUpdater

class SAITemplateRenderer:
    jinja2_env: Environment = None

    @classmethod
    def new_tm(cls, template_file_path: str, template_root):
        if cls.jinja2_env == None:
            cls.jinja2_env = Environment(loader=FileSystemLoader(template_root), trim_blocks=True, lstrip_blocks=True)
            cls.jinja2_env.add_extension('jinja2.ext.loopcontrols')
            cls.jinja2_env.add_extension('jinja2.ext.do')

        return cls.jinja2_env.get_template(template_file_path)

    def __init__(self, template_file_path: str, *, template_root):
        self.template_file_path = template_file_path
        self.tm = SAITemplateRenderer.new_tm(template_file_path, template_root)

    def render(self, **kwargs: Any) -> str:
        return self.tm.render(**kwargs)

    def render_to_file(self, target_file_path, **kwargs: Any) -> None:
        print(f"Updating file: {target_file_path} (template = {self.template_file_path}) ...")
        rendered_str = self.tm.render(**kwargs)
        SAIFileUpdater.write_if_different(target_file_path, rendered_str)
