# Instant Nginx Alpine Container serving pre-built static bundle
FROM nginx:alpine

COPY frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
