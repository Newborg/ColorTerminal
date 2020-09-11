import io
import sys

streamOut = io.StringIO()
streamOut.write("Testing")

sys.stdout = streamOut

print("First print line")
print("Second print line")

file = open("TestFile.txt","w")
file.write(streamOut.getvalue())
streamOut.close()

sys.stdout = file

print("Third print line")

file.close()
