import sys
with open(sys.argv[1], "r") as f:
    text = f.read()

offset = 0
limit = 1000
while offset < len(text):
    print(text[offset:offset+limit])
    offset += limit
