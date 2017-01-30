FROM python:latest
MAINTAINER Bahadir Katipoglu <bahadir.katipoglu@waplog.com>
LABEL description="Cyclops Docker Image"

RUN apt-get update
RUN pip install imagehash
RUN pip install requests
RUN pip install pymvptree
RUN pip install Flask
RUN pip install connexion
RUN pip install pika
RUN pip install redis
EXPOSE 9090
VOLUME /opt/data