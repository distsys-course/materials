FROM python:3.11.5-slim-bullseye

WORKDIR /application

# Copy the requirements file and download the dependencies.
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copy other data.
COPY . .

CMD [ "python3", "app.py"]