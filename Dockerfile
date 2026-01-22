FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Store initial key files and prices for restoration after volume mount
RUN mkdir -p /app/initial_data && \
    cp /app/data/keys/key*.txt /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/prices/prices.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/dashboard/auth.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/dashboard/admins.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/users/users.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/admin/admin.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/coupon/coupons.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/links/download.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/shortenurl/*.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/data/settings/settings.json /app/initial_data/ 2>/dev/null || true && \
    cp /app/orders.db /app/initial_data/ 2>/dev/null || true && \
    cp -r /app/data/dashboard/backgroundimg /app/initial_data/ 2>/dev/null || true

    

# Ensure data directories exist with write permissions
RUN mkdir -p /app/data/keys /app/data/coupon /app/data/links /app/data/shortenurl /app/data/prices /app/data/dashboard /app/data/admin /app/data/users /app/data/settings && \
    chmod -R 777 /app/data && \
    ls -la /app/data/keys/

EXPOSE 8080

CMD ["python", "app.py", "bot.py"]