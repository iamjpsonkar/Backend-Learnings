# Learnings

A personal, hands-on knowledge base for learning software engineering, backend development, infrastructure, and modern technology.

This repository brings together practical code samples, implementation exercises, technical notes, learning roadmaps, and interview preparation material. It is intended to evolve as new concepts are explored and existing notes are improved.

> **Learning approach:** Understand the concept → explore a working example → experiment with it → document the important details.

## Repository at a glance

| Area | What you'll find |
|---|---|
| [Cloud-Learnings](Cloud-Learnings/) | Cloud computing foundations, Linux, networking, AWS, Azure, GCP, containers, Kubernetes, IaC, CI/CD, security, and observability |
| [SYSTEM_DESIGN](SYSTEM_DESIGN/) | System design fundamentals, architecture concepts, design exercises, and worked system-design examples |
| [KUBERNETES](KUBERNETES/) | Kubernetes notes and hands-on manifests covering clusters, Pods, Deployments, replication, and Services |
| [DOCKER](DOCKER/) and [DockerLearn](DockerLearn/) | Docker fundamentals, commands, images, containers, and containerized application examples |
| [CRUD_Learnings](CRUD_Learnings/) | CRUD application examples using Flask and Sanic, plus authentication and authorization experiments |
| [FLASK_Learn](FLASK_Learn/) | Flask learning examples |
| [Django_learnings](Django_learnings/) | Django learning material and examples |
| [Sanic_Learnings](Sanic_Learnings/) | Sanic concepts, asynchronous code, class-based views, and API examples |
| [Alembic_Learn](Alembic_Learn/) | Database schema migration notes and examples with Alembic |
| [PostgreSQL_Learnings](PostgreSQL_Learnings/) | PostgreSQL learning notes and practical work |
| [WebLearnings](WebLearnings/) | Web development fundamentals and reference notes |
| [Nodejs_Learnings](Nodejs_Learnings/) and [MERN_Learnings](MERN_Learnings/) | JavaScript, Node.js, and MERN-stack experiments |
| [DS_ALGO](DS_ALGO/) | Data structures and algorithms practice |
| [Interview_PREP](Interview_PREP/) | Interview preparation notes, practice material, and interview logs |
| [GEN_AI_Learnings](GEN_AI_Learnings/) | Generative AI experiments, notebooks, setup files, and notes |
| [ML_Learnings](ML_Learnings/) | Machine learning learning material |
| [NGINX](NGINX/) | NGINX configuration and web-server examples |
| [Optimization_Learnings](Optimization_Learnings/) | Performance and optimization experiments |
| [Tkinter_Learn_udemy](Tkinter_Learn_udemy/) | Tkinter GUI examples and small applications |

## Suggested learning paths

These are suggested entry points through the material; the repository is a collection of notes and projects rather than a rigid course.

### Backend development

1. Explore [WebLearnings](WebLearnings/) for web fundamentals.
2. Explore [CRUD_Learnings](CRUD_Learnings/) and [FLASK_Learn](FLASK_Learn/) for API and CRUD patterns.
3. Continue with [Django_learnings](Django_learnings/) and [Sanic_Learnings](Sanic_Learnings/).
4. Study [PostgreSQL_Learnings](PostgreSQL_Learnings/) and [Alembic_Learn](Alembic_Learn/) for relational data and schema migrations.
5. Review [NGINX](NGINX/) for web-server and reverse-proxy concepts.

### Containers and orchestration

1. Start with [DOCKER](DOCKER/) or [DockerLearn](DockerLearn/).
2. Continue with [KUBERNETES](KUBERNETES/).
3. Use [Cloud-Learnings](Cloud-Learnings/) to connect container concepts with cloud infrastructure and DevOps.

### Cloud and DevOps

Follow the numbered sections in [Cloud-Learnings](Cloud-Learnings/), beginning with its foundations. The material progresses through cloud fundamentals, Linux, networking, cloud providers, containers, Kubernetes, infrastructure as code, automation, CI/CD, security, and observability.

### System design

Start with [SYSTEM_DESIGN/topics.md](SYSTEM_DESIGN/topics.md) for the topic outline, then use the [system-design notes](SYSTEM_DESIGN/README.md) and [system-design examples](SYSTEM_DESIGN/system-design-examples/) to practice turning requirements into architectures and evaluating trade-offs.

### Interview preparation

Use [Interview_PREP](Interview_PREP/) for the interview question bank, practice material, and interview notes. Pair it with [DS_ALGO](DS_ALGO/) for coding practice.

## How to use this repository

- **Browse by topic:** Open the relevant directory and start with its `README.md`, where available.
- **Run the examples:** Check the files and dependencies in the individual project directory before executing code.
- **Practice actively:** Modify examples, test edge cases, and try implementing the same concept in a different way.
- **Keep useful notes:** Capture explanations, commands, mistakes, debugging steps, and links to authoritative documentation.
- **Verify version-specific details:** Frameworks and infrastructure tools change; check the official documentation when a command or API may depend on the installed version.

## Working with the repository

Clone the repository:

```bash
git clone https://github.com/iamjpsonkar/Learnings.git
cd Learnings
```

Explore the folders:

```bash
ls
```

Most examples are independent. Before running one, navigate to its directory and inspect its README, dependency files, configuration, and setup instructions. Python examples may use virtual environments:

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1
```

Install dependencies only when the relevant project provides a `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Repository structure

The repository contains topic-based directories rather than one application with a single runtime. Some directories contain structured Markdown courses, while others contain scripts, notebooks, configuration files, or small projects.

A directory may also contain its own README with more detailed instructions. Prefer those local instructions when working on a specific topic.

## Contributing and corrections

This is a continuously evolving learning repository. Improvements are welcome:

- Fix incorrect or outdated explanations.
- Add clear examples and practical exercises.
- Include setup and execution instructions for runnable projects.
- Link to the official documentation or original learning resource.
- Keep topic-specific material in the relevant directory.

## Disclaimer

The code and notes are provided for learning and experimentation. Review commands, configurations, and dependencies before using them in production environments. Examples may require adaptation for your operating system, tool versions, or infrastructure.

---

**Explore, build, break, debug, and document.**
