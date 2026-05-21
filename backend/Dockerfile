# Usamos una versión LTS y 'slim' (ligera pero con lo necesario para compilar)
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc en el disco (equivalente a no guardar caché innecesario)
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python guarde los logs en un buffer, permitiendo ver los errores en tiempo real en Docker
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalamos dependencias del sistema necesarias para PostgreSQL y compilación
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalamos Poetry
RUN pip install --upgrade pip \
    && pip install poetry

# PUENTE LÓGICO: En desarrollo local de Python creamos "Entornos Virtuales" (VMs) 
# para no ensuciar el SO. Pero como un contenedor de Docker YA ES un entorno aislado, 
# le decimos a Poetry que instale las librerías globalmente dentro del contenedor.
RUN poetry config virtualenvs.create false

# Copiamos SOLO los archivos de dependencias primero (Explicación abajo)
COPY pyproject.toml poetry.lock* /app/

# Instalamos las dependencias (si existen)
RUN if [ -f pyproject.toml ]; then poetry install --no-root --no-interaction --no-ansi; fi

# Finalmente copiamos el resto del código
COPY . /app/