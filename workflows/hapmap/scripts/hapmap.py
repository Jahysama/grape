import os
import subprocess
import networkx as nx
import pandas
from itertools import combinations


BCFTOOLS = "bcftools"


def bcftools_index(infile, how):
    args = [BCFTOOLS, 'index', '--force', '-f', infile]
    if how == 'csi':
        args.append('-c')
    else:
        args.append('-t')

    pipes = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = pipes.communicate()
    if pipes.returncode != 0:
        print(std_out.decode())
        raise Exception(std_err.decode())
    return


def extract_population_samples(infile, tempfile, outfile, relations_file, samples_file, populations):
    data = pandas.read_csv(relations_file, sep='\t')
    data = data.loc[(data.population.isin(populations) & (data.IID != 'NA12236')), :]
    samples = data.IID.tolist()
    with open(samples_file, 'w') as file:
        file.writelines(str(s) + '\n' for s in samples)

    print('samples are in form: ', samples[0:2])
    args = [BCFTOOLS, 'view', '--force-samples', '--samples-file', samples_file, '-O', 'z', '-o', tempfile, infile]
    pipes = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = pipes.communicate()
    if pipes.returncode != 0:
        print(std_out.decode())
        raise Exception(std_err.decode())
    new_samples = bcftools_samples(tempfile)
    print('missing sample: ', set(samples) - set(new_samples))
    fid_iids = (data.FID + '_' + data.IID).tolist()
    with open(samples_file, 'w') as file:
        file.writelines(str(s) + '\n' for s in fid_iids)

    bcftools_reheader(tempfile, samples_file, outfile)
    return

def bcftools_samples(infile):
    """Return individual ids of given vcf file"""
    #if not os.path.exists(infile + '.csi'):
    #    bcftools_index(infile)
    args = [BCFTOOLS, 'query', '-l', infile]
    pipes = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = pipes.communicate()
    if pipes.returncode != 0:
        print(std_out.decode())
        raise Exception(std_err.decode())
    return std_out.decode().split()


def read_hapmap_pedigree(filename, populations):

    pedigree = nx.DiGraph()
    data = pandas.read_csv(filename, sep='\t')
    data = data.loc[data.population.isin(populations), :]
    for i, row in data.iterrows():
        if row['dad'] != '0':
            pedigree.add_edge(row['dad'], row['FID'] + '_' + row['IID'])
        if row['mom'] != '0':
            pedigree.add_edge(row['mom'], row['FID'] + '_' + row['IID'])
    return data, pedigree


def get_kinship(pedigree):
    # get all the descendants (0 length means self)
    v_relatives_ = list(nx.shortest_path_length(pedigree))
    v_relatives = []
    for i, v in v_relatives_:
        temp = {}
        for j in v:
            if v[j] != 0:
                # remove self relationship
                temp[j] = v[j]
        v_relatives.append((i, temp))

    relatives = nx.Graph()
    for ancestor, descendants in v_relatives:
        for i, j in combinations(descendants, 2):
            # len(descendants) = 0/1 will return []
            degree = descendants[i] + descendants[j]
            if relatives.has_edge(i, j):
                if relatives[i][j]['degree'] > degree:
                    relatives.add_edge(i, j, common_ancestor=ancestor, degree=degree)
                elif relatives[i][j]['degree'] == degree:
                    pass  # below will print not only the lowest common ancestry
                    #print("{} and {} has ancestor {} and {}".format(i, j, relatives[i][j]['common_ancestor'], ancestor))
                    #relatives[i][j]['common_ancestor2'] = ancestor
            else:
                relatives.add_edge(i, j, common_ancestor=ancestor, degree=degree)
        # add vertical relationship
        for m in descendants:
            relatives.add_edge(ancestor, m, common_ancestor=ancestor, degree=descendants[m])

    return v_relatives, relatives


def write_pedigree(rel_data, outfile):
    to_write = rel_data.loc[:, ['FID', 'IID', 'dad', 'mom', 'sex', 'pheno']]
    to_write.to_csv(outfile, sep='\t', index=False, header=None)


def bcftools_reheader(infile, sample, outname=None):
    """Rename vcf samples given a sample file"""
    if not outname:
        outname = infile

    # workaround of https: // github.com / samtools / bcftools / issues / 1288
    vcf_uncompressed = infile[:-3]  # remove .gz
    view_args = [BCFTOOLS, 'view', infile, '-O', 'v', '-o', vcf_uncompressed]
    pipes = subprocess.Popen(view_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = pipes.communicate()
    if pipes.returncode != 0:
        print(std_out.decode())
        raise Exception(std_err.decode())

    vcf_reheaded = vcf_uncompressed[:-4] + '.reheaded.vcf'
    args = [BCFTOOLS, 'reheader', vcf_uncompressed, '-s', sample, '-o', vcf_reheaded]
    pipes = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = pipes.communicate()
    if pipes.returncode != 0:
        print(std_out.decode())
        raise Exception(std_err.decode())

    args = [BCFTOOLS, 'view', vcf_reheaded, '-Oz', '-o', outname]
    pipes = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = pipes.communicate()
    if pipes.returncode != 0:
        print(std_out.decode())
        raise Exception(std_err.decode())

    os.remove(vcf_reheaded)
    os.remove(vcf_uncompressed)
    return outname


if __name__ == "__main__":
    print('input:')
    print(snakemake.input)
    print(snakemake.input.keys())
    populations = {'CEU'}

    rel_data, pedigree = read_hapmap_pedigree(snakemake.input['fam'], populations)
    _, kinship = get_kinship(pedigree)
    kin_name = snakemake.output['kin']
    nx.write_edgelist(kinship, kin_name, data=True)

    write_pedigree(rel_data, snakemake.output['fam'])

    extract_population_samples(snakemake.input['vcf'], snakemake.output['iid_vcf'],
                               snakemake.output['vcf'], snakemake.input['fam'],
                               snakemake.output['samples'], populations)
    bcftools_index(snakemake.output['vcf'], how='csi')
    bcftools_index(snakemake.output['vcf'], how='tbi')

