# BA3073 source submission

Student: Wen Quan (2330024244)

This folder is a clean snapshot of the supplied project with the assignment
changes. It excludes local secrets, runtime data, dependencies, generated academic
artifacts and the original repository's Git history. The original README retains
the assignment requirements.

## Implemented changes

- `backend/pipelines/essay_html.py`: report instructions covering the three tasks,
  real evidence, technical explanations, security/cost analysis and a 20-page cap.
- `frontend/src/app.js` and `frontend/src/artifact-download.js`: application Bearer
  tokens use `X-App-Authorization`, leaving `Authorization` for Nginx Basic Auth.
- `backend/api/`: all protected API families accept the application header and
  retain legacy Bearer support. Invalid explicit application credentials do not
  fall back to another session.
- `backend/tests/test_auth_sqlite.py` and the artifact download test: regression
  coverage; 56 focused backend tests and 12 frontend tests passed locally.
- `backend/static/`: rebuilt frontend included because the Dockerfile copies
  these assets and does not build the frontend itself.
- Authentication contract and ADR 012 document the transport compatibility change.

## Run and build

Start Docker and run from this folder:

```bash
docker compose -p ai-learning-assistant up --build -d
curl -fsS http://127.0.0.1:14242/health
```

Configure a personal API key through the app, or privately create
`data/model-secrets.env` containing `MODEL_API_KEY=your_key`. This file must never
be committed. No working credentials are supplied in this repository.

When changing frontend source, first run:

```bash
npm --prefix frontend ci
npm --prefix frontend run build
```

Then rebuild the Docker image. Linux x86_64 ECS requires `--platform linux/amd64`
when building on an ARM64 Mac.

## Deployment notes

Task 2 used the restricted direct-IP Guangzhou deployment. Task 3 used Hong Kong,
with a loopback-only `127.0.0.1:14242:14242` container port mapping and host Nginx
providing HTTPS plus independent Basic Auth. The root `compose.yml` is the local
build configuration, not a replacement for the cloud deployment configuration.

For browser Basic Auth, begin a fresh session at `https://ai.timcloudlab.win/`
rather than directly at `/ui/`, so browser credential reuse covers API paths.
The user verified that root-path entry resolved the repeated prompts after v2.

## Separate coursework submission

Submit the final report, `local-ui-check.txt` and `ecs-docker-check.txt` separately
as requested by the assignment. They are deliberately excluded from this source
snapshot. Keep private keys, passwords, SQLite data, model secrets and generated
workspace contents out of GitHub.
