import pandas


def transform(input_ibd, output_ibd):
    names = [
        'sample1',
        'sample2',
        'chrom',
        'phys_start_pos',
        'phys_end_pos',
        'IBD_type',
        'genetic_start_pos',
        'genetic_end_pos',
        'genetic_seg_length',
        'marker_count',
        'error_count',
        'error_density'
    ]
    data = pandas.read_table(input_ibd, header=None, names=names)
    data.loc[:, 'id1'] = data.sample1.str.replace(':', '_') + ' ' + data.sample1.str.replace(':', '_')
    data.loc[:, 'id2'] = data.sample2.str.replace(':', '_') + ' ' + data.sample2.str.replace(':', '_')
    # awk '{{sub(":", "_", $1); sub(":", "_", $2); print $1, $1 "\t" $2, $2 "\t" $3 "\t" $4, $5 "\t" 0, 0 "\t" $10 "\t" $9 "\t" "cM" "\t" 0 "\t" 0 "\t" 0}};
    data.loc[:, 'phys_pos'] = [f'{start} {end}' for start, end in zip(data.phys_start_pos, data.phys_end_pos)]
    data.loc[:, 'zero1'] = '0 0'
    data.loc[:, 'zero2'] = '0'
    data.loc[:, 'cM'] = 'cM'
    data.loc[:, 'ibd21'] = [2 if ibd_type == 'IBD2' else 0 for ibd_type in data.IBD_type]
    data.loc[:, 'ibd22'] = data.ibd21
    to_write = data.loc[:, ['id1', 'id2', 'chrom', 'phys_pos', 'zero1', 'marker_count', 'genetic_seg_length', 'cM', 'zero2', 'ibd21', 'ibd22']]
    to_write.to_csv(output_ibd, index=False, header=None, sep='\t')


if __name__ == '__main__':

    ibd = snakemake.input['ibd']
    output = snakemake.output['germline']
    transform(ibd, output)