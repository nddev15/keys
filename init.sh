#!/bin/bash

# Function to restore file if it doesn't exist
restore_if_missing() {
    local dest_file=$1
    local src_file="/app/initial_data/$(basename $dest_file)"
    
    if [ ! -f "$dest_file" ] && [ -f "$src_file" ]; then
        echo "Restoring $dest_file from $src_file"
        cp "$src_file" "$dest_file"
    fi
}

# Restore all critical files
restore_if_missing "/app/data/dashboard/auth.json"
restore_if_missing "/app/data/dashboard/admins.json"
restore_if_missing "/app/data/users/users.json"
restore_if_missing "/app/data/admin/admin.json"
restore_if_missing "/app/data/coupon/coupons.json"
restore_if_missing "/app/data/links/download.json"
restore_if_missing "/app/data/prices/prices.json"
restore_if_missing "/app/data/settings/settings.json"
restore_if_missing "/app/data/dashboard/user_settings.json"
restore_if_missing "/app/orders.db"

# Restore key files
for key_file in /app/initial_data/key*.txt; do
    if [ -f "$key_file" ]; then
        filename=$(basename "$key_file")
        if [ ! -f "/app/data/keys/$filename" ]; then
            echo "Restoring /app/data/keys/$filename"
            cp "$key_file" "/app/data/keys/$filename"
        fi
    fi
done

# Restore shortenurl files
for url_file in /app/initial_data/*.json; do
    if [[ $(basename "$url_file") == *"url"* ]] || [[ $(basename "$url_file") == "isgd.json" ]] || [[ $(basename "$url_file") == "tinyurl.json" ]]; then
        filename=$(basename "$url_file")
        if [ ! -f "/app/data/shortenurl/$filename" ]; then
            echo "Restoring /app/data/shortenurl/$filename"
            cp "$url_file" "/app/data/shortenurl/$filename"
        fi
    fi
done

# Restore background images if exists
if [ -d "/app/initial_data/backgroundimg" ] && [ ! -d "/app/data/dashboard/backgroundimg" ]; then
    echo "Restoring background images"
    cp -r "/app/initial_data/backgroundimg" "/app/data/dashboard/"
fi

# Set permissions
chmod -R 777 /app/data

echo "File restoration completed"

# Start the application
exec python app.py bot.py