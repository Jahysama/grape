rule convert_23andme_to_plink:
    input:
        get_samples_path
    output:
        expand("plink/{{sample}}.{ext}", ext=PLINK_FORMATS)
    params:
        get_samples_name
    conda:
        "../envs/plink.yaml"
    log:
        "logs/plink/convert_23andme_to_plink-{sample}.log"
    benchmark:
        "benchmarks/plink/convert_23andme_to_plink-{sample}.txt"
    shell:
        """
        # by default plink write output in the same --out option. need to use tee to redirect
        plink --23file {input} {params} {params} i --output-chr M --export vcf bgz --out plink/{params} | tee {log}
        """

rule merge_to_vcf:
    input:
        expand("plink/{sample}.{ext}", sample=SAMPLES_NAME, ext=PLINK_FORMATS)
    output:
        plink_clean     = expand("plink/{i}_clean.{ext}", i=SAMPLES_NAME, ext=PLINK_FORMATS),
        plink_merged    = expand("vcf/merged.{ext}", ext=PLINK_FORMATS),
        vcf             = "vcf/merged.vcf.gz",
        merge_list      = "plink/merge.list"
    conda:
        "../envs/bcftools.yaml"
    log:
        "logs/vcf/merge_to_vcf.log"
    benchmark:
        "benchmarks/plink/merge_to_vcf.txt"
    shell:
        """
        true > {output.merge_list} && for i in {SAMPLES_NAME}; do echo "plink/$i" >> {output.merge_list}; done
        # -m none creates multiple records for each new multiallelic variant
        bcftools merge -m none --file-list {output.merge_list} -O z -o vcf/merged_mapped_sorted.vcf.gz | tee -a {log}
        """

rule recode_vcf:
    input: vcf=rules.merge_to_vcf.output['vcf']
    output: vcf = "vcf/merged_recoded.vcf.gz"
    conda: "../envs/plink.yaml"
    shell: "plink --vcf {input.vcf} --snps-only just-acgt --output-chr M --not-chr XY,MT --export vcf bgz --out vcf/merged_recoded"

rule liftover:
    input:
        vcf=rules.recode_vcf.output['vcf'],
        chain='/media/ref/hg38ToHg19.over.chain.gz',
        ref='/media/ref/human_g1k_v37.fasta'
    output:
        vcf="vcf/merged_lifted.vcf"

    singularity: "docker://alexgenx/picard:latest"
    shell:
        """
            #java -jar /picard/picard.jar CreateSequenceDictionary R={input.ref} 
                 
            java -jar /picard/picard.jar LiftoverVcf I={input.vcf} O={output.vcf} CHAIN={input.chain} REJECT=vcf/rejected.vcf R={input.ref}
                
        """