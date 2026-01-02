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

  services = {
    # NOTE: Database
    postgres = {
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
    # NOTE: Celery broker
    redis = {
      enable = true;
    };
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

    celery-worker = {
      process-compose.depends_on.redis.condition = "process_healthy";
      exec = "celery -A watchtower_ce worker -l INFO";
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
    ai.module =
      let
        buildInputs = with pkgs; [
          cudaPackages.cudatoolkit
          cudaPackages.cuda_cudart
          cudaPackages.cudnn
          libuv
          zlib
        ];
      in
      {
        packages = with pkgs; [ cudaPackages.cuda_nvcc ];

        env = {
          LD_LIBRARY_PATH = "${lib.makeLibraryPath buildInputs}:/run/opengl-driver/lib:/run/opengl-driver-32/lib";
          XLA_FLAGS = "--xla_gpu_cuda_data_dir=${pkgs.cudaPackages.cudatoolkit}";
          CUDA_PATH = pkgs.cudaPackages.cudatoolkit;
          # WARN: Required for llama-cpp-python to enable CUDA backend
          CMAKE_ARGS = "-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=\"75;86;89;120\"";
        };

        languages.python.uv.sync = {
          enable = false;
          groups = [ "ai" ];
          extras = [ "models" ];
        };
      };
  };
}
