# Readme

## Server setup
 - Run as root
 - Install podman `apt-get -y install podman`
 - create group thempods `groupadd thempods`
 - add live `useradd -m -g thempods live`
 - add staging `useradd -m -g thempods staging`
 - check uid ranges for these users and groups to make sure that they are not overlapping. `grep live /etc/subuid /etc/subgid` `grep staging /etc/subuid /etc/subgid`. If they are overlapping, use https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md#etcsubuid-and-etcsubgid-configuration
 - 


## Example folder structure

- .github
  - workflows
    - build.yml
    - test.yml
    - deploy.yml
- applications 
  - chatbot
    - src
    - dockerfile
  - docker-compose.yaml # defines all applications for local development
- deployments
  - chatbot
    - docker-compose.yaml
    - example.env # gitignored, per environment we implement the .env file
  - tradingbot, webapp, etc.
  - postgres
    - docker-compose.yaml
    - example.env # gitignored, per environment we implement the .env file
    - config.conf
  - mongodb, redis, litellm, chromadb, nginx, etc.
- workers # to be figured out
- README
- .gitignore
- etc

### Todo
- How to handle environment specific configurations for networking. 
- install a log aggregator such as fluentbit.io

## Continuous Deployment Process
  - ssh to build server and trigger build
    - run tests
    - create docker images
    - publish docker images
  - ssh to staging server 
    - download the artifact
    - deploy the version
    - run acceptance tests
    - if it fails, notify user and stop the process - your staging is down, you need to fix it now! 
  - ssh to live server
    - download the artifact
    - deploy the version
    - run acceptance tests 
