#!/bin/bash

# This script lists all files in the current directory and displays their contents
# in a specific format.

# Get a list of all files in the current directory
files=$(find ./src/gitreviewer -maxdepth 5 -type f -print | sort | grep "git.py" | grep -v "pyc")

# Initialize a counter for files
file_count=0
total_files=$(echo "$files" | wc -l)

# Loop through each file
printf '```'
echo "#\n#"
for file in $files; do
    # Increment file count
    file_count=$((file_count + 1))

    # Print the file name
    echo "# --- start content from file ${file#./} ---"

    # Print the content of the file
    cat "$file"

    # Print the separator if it's not the last file
    if [ "$file_count" -lt "$total_files" ]; then
        echo "" # Add an empty line for separation
        echo "# --- end content from file ${file#./} ---"
        echo "" # Add an empty line for separation
    fi
done
printf '```'

