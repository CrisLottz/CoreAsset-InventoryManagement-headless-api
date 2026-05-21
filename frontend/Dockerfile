FROM node:20-alpine

WORKDIR /app

# Igual que en el backend, aprovechamos el caché de Docker con package.json
#COPY package*.json ./

RUN if [ -f package.json ]; then npm install; fi

COPY . .

# Exponemos el puerto de Vite
EXPOSE 5173

# El comando por defecto para desarrollo (con host para exponerlo fuera del contenedor)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]