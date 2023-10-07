def get_image_caption(image_url):
    return str(abs(hash(image_url)) % (10 ** 8))
