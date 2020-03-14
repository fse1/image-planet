FROM ubuntu:18.04

RUN apt-get update

# Set the home directory to /root
ENV HOME /root

# cd into the home directory
WORKDIR /root

# Install Python
RUN apt-get update --fix-missing
RUN apt-get install -y python3.7

# Copy all app files into the image
COPY . .

# Change Directory
RUN cd src/

# Allow port 8000 to be accessed from outside the container
EXPOSE 8000

# Run the app
CMD ["python3", "web_server.py"]
