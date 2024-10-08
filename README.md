
# Hilbert - application for text classification
This is a student project completed for class. It has been done as a team work of 5 people. Original repository where all the work were uploaded in the real time: https://github.com/Majkel1999/Hilbert .
Project has been uploaded there to show my part of work which is FE part of application.

Hilbert is a web application, designated for text classification. It implements a BERT model, trained via Human-in-the-Loop tactics.

[![CodeQL](https://github.com/Majkel1999/Hilbert/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/Majkel1999/Hilbert)
---
## Deploying

---

Creating your own instance of the application is as easy as this:

```
https://github.com/Kacper12445/Hilbert-Project.git
cd Hilbert-Project
docker-compose up 
```

In order to change configuration, edit **.env** file in root directory. By default it hosts all services at **localhost:8000**. 

For more information, consult [official docker-compose documentation](https://docs.docker.com/compose/).

Current endpoints are:
- / - frontend
- /api/v1 - Api service
- /api/v1/docs - Swagger documentation
- /prometheus - Prometheus dashboard
- /rabbitmq - RabbitMQ Management plugin
- /grafana - Grafana with 2 dashboards for monitoring

For more information, consult official [Traefik routing documentation](https://doc.traefik.io/traefik/routing/overview/).

---
