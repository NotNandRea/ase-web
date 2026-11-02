"""Adapter: does what ASE Studio's "Run" button does, without the HTTP server

It contains no backend logic. It calls the original functions of the original
backend in the same order the original Handler, copying its code

  create_project():
    POST /api/projects  -> create an empty project from the template
  run():
    1. POST /api/config    -> store the CPU configuration
    2. POST /api/run       -> store the source, build, simulate
    3. GET  /api/pipeline  -> read gem5 output and turn it into JSON

Differences from the Handler:
  - no json is sent, now it returns a dictionary with the same content the Handler would send
  - /api/config is called here because a worker job carries source and
    configuration together
  - /api/pipeline is called after a successful run, because the worker
    executes the whole job at once. Then the frontend asks for it as a second
    request only if the run succeeded.
  - Errors raised return {"error": message, "status": status}:
    the same body the Handler sends, with the HTTP status code inside it.
"""

from ase_studio import backend


def create_project(name):
    """Create an empty project exactly like POST /api/projects.

    main.s comes from the backend's TEMPLATE and the Makefile from its
    MAKEFILE, so every job uses the structure of the current backend version.
    """
    try:
        # POST /api/projects
        name = backend.validate_project_name(name)
        destination = backend.project_path(name) # builds the path to programs/name starting from ASE_STUDIO_HOST_ROOT, it is ASE_STUDIO_HOST_ROOT/programs/{name}
        if destination.exists(): backend.fail("A project with that name already exists.")
        destination.mkdir(); (destination / "main.s").write_text(backend.TEMPLATE); (destination / "Makefile").write_text(backend.MAKEFILE)
        return {"ok": True, "name": name}

    except ValueError as error:
        # Same as the Handler
        message, status = error.args[0]
        return {"error": message, "status": status}


def run(name, text, config, allow_scaffold_edit=False):
    """Run project 'name' like the Run button and return a dictionary.

    name                 project folder name inside programs/
    text                 content of main.s (the "text" field of /api/run)
    config               CPU configuration (the "config" field of /api/config)
    allow_scaffold_edit  the "allowScaffoldEdit" field of /api/run
    """
    try:
        # POST /api/config
        backend.save_project_config(backend.project_dir(name), config)

        # POST /api/run
        backend.save_source(backend.project_dir(name), text, allow_scaffold_edit)
        built = backend.build(name)
        if not built["ok"]:
            return {"ok": False, "phase": "build", "output": built["output"],
                    "advancedOutput": built["advancedOutput"]}
        simulated = backend.simulate(name)
        result = {"ok": simulated["ok"], "phase": "simulate",
                  "output": built["output"] + "\n" + simulated["output"],
                  "advancedOutput": built["advancedOutput"] + "\n" + simulated["advancedOutput"]}

        # GET /api/pipeline
        if result["ok"]:
            result["pipeline"] = backend.pipeline_for_display(name)
        return result

    except ValueError as error:
        # Same as the Handler
        message, status = error.args[0]
        return {"error": message, "status": status}