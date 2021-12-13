import os
import json

def split_chip():
    with open('config.temp') as config:
        data = json.load(config)
        num_runs = data[0]
        num_founders = data[1]
    with open('list.samples', "r") as f:
        lines = f.readlines()
        samples_list = [line.rstrip() for line in lines]
    for i in range(0, num_runs*(num_founders-1), num_founders):
        sample = samples_list[i:i + num_founders]
        with open("sample.txt", "w") as s:
            s.write("\n".join(sample))
        seg = int(i/num_founders)
        #print(f"bcftools view -s sample.txt pedsim/phased/background.vcf.gz > segment{seg}.vcf.gz")
        os.system(f"bcftools view -S sample.txt pedsim/phased/background.vcf.gz > segment{seg}.vcf.gz --force-samples")


if __name__ == '__main__':
    split_chip()
