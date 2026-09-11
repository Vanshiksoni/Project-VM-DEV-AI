# Docker

## What is Docker?

Docker is a platform used to package applications and their dependencies into lightweight, portable containers. Containers allow applications to run consistently across different environments.

## Docker Containers

A Docker container is an isolated runtime environment containing an application and the dependencies required to run it. Containers share the host operating system kernel but remain isolated from other containers.

## Dockerfile

A Dockerfile is a text file containing instructions used to build a Docker image. Common instructions include FROM, RUN, COPY, WORKDIR, and CMD.

## Docker Image

A Docker image is a read-only template used to create containers. Images contain the application code, libraries, dependencies, and configuration required by the application.

## Docker Compose

Docker Compose is a tool used to define and run multi-container applications. A Compose configuration describes services, networks, volumes, and other resources required by an application.

## Common Docker Commands

### Build an image

docker build -t myapp .

### Run a container

docker run myapp

### List running containers

docker ps

### Stop a container

docker stop <container>

## Docker and DevAssist AI

DevAssist AI can use technical documentation such as this document as a knowledge source. During the retrieval stage, relevant sections can be retrieved and provided to the language model as context.
