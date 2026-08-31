FROM nginx:1.27-alpine

RUN rm -rf /usr/share/nginx/html/*
COPY index.html feedback.js /usr/share/nginx/html/

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --spider -q http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]