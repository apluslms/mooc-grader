# run-mooc-grader

A Docker container that runs the MOOC-grader for A+ exposed to port 8080.

Note that the MOOC-grader only provides hosting of interactive
course material. The [A-plus front](https://hub.docker.com/r/apluslms/run-aplus-front/)
is required to display the user interface and to store records in the database.

See the [A-plus manual course](https://github.com/apluslms/aplus-manual)
that includes a Docker Compose configuration file to develop and test course content.

## Usage

MOOC-grader is installed in `/srv/grader`.
You can mount a development version of the MOOC-Grader source code to `/src/grader`.
The container will then copy it to `/srv/grader` and compile
the translation file (django.po). If you mount directly to
`/srv/grader`, you need to manually compile the translation file beforehand,
but on the other hand, Django can reload the code and restart the server
without restarting the whole container when you edit the source code files.

Location `/data` is a volume and contains exercise data, database and secret key.
It is world-writable, thus you can run this container as a normal user.

The course (git) directory should be mounted to `/srv/courses/default`.
The course directory name `default` is hardcoded in the scripts
inside the container.

Partial example of `docker-compose.yml` (volumes are optional of course):

```yaml
services:
  grader:
    image: apluslms/run-mooc-grader
    volumes:
    # required
    - /var/run/docker.sock:/var/run/docker.sock
    - /tmp/aplus:/tmp/aplus
    # mount a course directory (current dir presumed to be a course repo)
    - .:/srv/courses/default:ro
    # named persistent volume (until removed)
    # - data:/data
    # development mounts
    # - /home/user/mooc-grader/:/src/grader/:ro
    # or...
    # - /home/user/mooc-grader/:/srv/grader/
    ports:
      - "8080:8080"
volumes:
  data:
```
