#!/usr/bin/env python3

import struct

array = []

array.append(10)
array.append(20)
array.append([30])


print(array)

dic = {}

dic["nice"] = "nice"
dic["yeah"] = { "diggah": [10, 20, 30] }
print(dic)

print(dic["yeah"]["diggah"][0])

testvar = int()

print(type(testvar))


text1 = "nice"
text1 += " nice2"

print(text1)

test = int()
test2 = float()
test3 = bytes([0x00, 0xF4, 0x61, 0x3B, 0x00, 0xF4, 0x61, 0x3B, 0x00, 0xF4, 0x61, 0x3B])
test4 = bytes()

print(test4)
print(test4[1:])