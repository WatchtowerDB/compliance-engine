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
        extras = [
          "dev"
          "tests"
        ];
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

  treefmt = {
    enable = true;
    config.programs = {
      ruff-check.enable = true;
      ruff-format.enable = true;
      prettier.enable = true;
      nixfmt.enable = true;
      taplo.enable = true;
      shellcheck.enable = true;
      shfmt.enable = true;
    };
  };

  git-hooks.hooks = {
    treefmt.enable = true;
  };

  profiles = {
    ai.module = {
      env = {
        # WARN: Required for llama-cpp-python to enable CUDA backend
        CMAKE_ARGS = "-DGGML_CUDA=on";
      };

      languages.python.uv.sync = {
        groups = [ "ai" ];
        extras = [ "models" ];
      };
    };
  };
}
