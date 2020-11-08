from random import randint

buckets = 1000
rounds = 1000000

random_choice = [0 for i in range(buckets)]
power_of_two_choices = [0 for i in range(buckets)]

for i in range(rounds):
  random_choice[randint(0, buckets - 1)] += 1
  first = randint(0, buckets - 1)
  second = randint(0, buckets - 1)
  if power_of_two_choices[first] < power_of_two_choices[second]:
    power_of_two_choices[first] += 1
  else:
    power_of_two_choices[second] += 1

print('Max random : ', max(random_choice))
print('Max P2C    : ', max(power_of_two_choices))
