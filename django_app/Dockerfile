FROM python:3.10-alpine

# Stel de werkmap in binnen de container, dit is de root van je Django-app
WORKDIR /code

# Kopieer requirements.txt en installeer afhankelijkheden
COPY requirements.txt /code/
RUN pip install -r requirements.txt

# Kopieer de rest van je Django-project
COPY . /code/

# Stel de standaard omgevingsvariabelen in voor de database
# Deze worden overschreven door docker-compose.yml, behalve DJANGO_SETTINGS_MODULE
ENV DB_NAME=myquoteproject_db
ENV DB_USER=myuser
ENV DB_PASSWORD=mypassword
ENV DB_HOST=db
ENV DB_PORT=5432
ENV DJANGO_SETTINGS_MODULE=core.settings 

# Exposeer de poort waarop Django zal draaien
EXPOSE 8000