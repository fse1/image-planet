FROM python:3.7-buster

# Set the home directory to /imageplanet
ENV HOME /imageplanet

# cd into the home directory
WORKDIR /imageplanet

# Copy all app files into the image
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Change Directory
WORKDIR /imageplanet/src

# Set necessary environment variables
ENV FLASK_APP web_server.py

# Allow port 5000 to be accessed from outside the container
EXPOSE 5000

# Add fix for waiting for DB container
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.1/wait /wait
RUN chmod +x /wait

# Run the app
CMD /wait && python -m flask init-db && python -m flask run --port 5000 --host 0.0.0.0
