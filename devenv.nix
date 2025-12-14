{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  env = {
    PYTHONPATH = "${config.git.root}/src";
    DJANGO_SETTINGS_MODULE = "watchtower_ce.settings";
    DJANGO_ENVIRONMENT = "PROD";
    DJANGO_DB_USER = "dev";
    DJANGO_DB_PASSWORD = "dev";
  };

  languages.python = {
    enable = true;
    version = "3.13";
    venv.enable = true;
    uv = {
      enable = true;
      sync = {
        enable = true;
        allGroups = true;
        allExtras = true;
      };
    };
  };

  services.postgres = {
    enable = true;
    listen_addresses = "localhost";
    initialDatabases = [
      {
        name = "watchtower_ce";
        user = "dev";
        pass = "dev";
      }
    ];
  };

  processes = {
    dbmigrate = {
      process-compose.depends_on.postgres.condition = "process_healthy";
      exec = ''
        django-admin makemigrations
        django-admin migrate
      '';
    };

    devserver = {
      process-compose.depends_on.dbmigrate.condition = "process_completed_successfully";
      exec = ''
        django-admin runserver
      '';
    };
  };

  git-hooks.hooks = {
    nixfmt.enable = true;
    ruff.enable = true;
    ruff-format.enable = true;
    prettier.enable = true;
  };
}
