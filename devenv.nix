{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    version = "3.13";
    uv = {
      enable = true;
      sync = {
        enable = true;
        allGroups = true;
        allExtras = true;
      };
    };
    venv.enable = true;
  };
}
