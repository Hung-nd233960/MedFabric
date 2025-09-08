FROM postgres:17.6

# Set default environment variables if not using Compose
ENV POSTGRES_USER=medfabric_user
ENV POSTGRES_PASSWORD=medfabric_pass
ENV POSTGRES_DB=medfabric_db

# Copy the backup.sql into the image
COPY backup.sql /docker-entrypoint-initdb.d/backup.sql