{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    version = "3.13";
    uv.enable = true;
    venv = {
      enable = true;
      requirements = builtins.readFile ./deps/dev.requirements.txt;
    };
  };

}
