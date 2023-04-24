with open('clustering_f.txt', 'r') as f:
    lines = f.readlines()
    with open('flat_clustering.txt', 'w') as out:
        for line in lines:
            url, value = line.split(',', maxsplit=1)
            url = url.strip("[]'")
            out.write(url + ',' + value)