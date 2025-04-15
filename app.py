# Import Streamlit UI Libraries
import streamlit as st
from streamlit_extras.colored_header import colored_header
from streamlit_extras.dataframe_explorer import dataframe_explorer as dfe
from streamlit_extras.stateful_button import button

# Import python packages
import os
import pandas as pd
import matplotlib.pyplot as plt

from anonymeter.evaluators import SinglingOutEvaluator
from anonymeter.evaluators import LinkabilityEvaluator
from anonymeter.evaluators import InferenceEvaluator

def headers(label_str,desc_str):
    colored_header(
        label=label_str,
        description=desc_str,
        color_name="light-blue-70")

def analyze_all(ori,
                syn,
                control,
                num_sout_attacks,
                num_link_attacks,
                num_neighbors_linkability, 
                auxiliary_columns1, 
                auxiliary_columns2
                ):
    # Singling Out
    status.update(label = "Measuring Singling Out Risk...", state='running',expanded=False)
    evaluator = SinglingOutEvaluator(ori=ori, 
                                     syn=syn, 
                                     control=control,
                                     n_attacks=num_sout_attacks)
    
    try:
        evaluator.evaluate(mode='univariate')
        srisk = evaluator.risk()
        print(srisk)
        srisk_val = srisk.value 
        ci_from = srisk.ci[0] 
        ci_to = srisk.ci[1]
        
        srisk_score = 100 - 100 * srisk_val
        sci_from = 100 * (1-ci_from)
        sci_to = 100 * (1-ci_to)
        st.session_state['srisk_score'] = srisk_score
        st.session_state['sci_from'] = sci_from
        st.session_state['sci_to'] = sci_to
    except RuntimeError as ex: 
        st.write(f"Singling out evaluation failed with {ex}. Please re-run this cell."
              "For more stable results increase `n_attacks`. Note that this will "
              "make the evaluation slower.")
    status.update(label = ":dna: Singling Out: "+str(round(srisk_score,2)), state='running',expanded=False)
    # Linkability
    status.update(label = "Measuring Linkability Risk...", state='running',expanded=False)   
    aux_cols = [
        ['type_employer', 'education', 'hr_per_week', 'capital_loss', 'capital_gain'],
        [ 'race', 'sex', 'fnlwgt', 'age', 'country']
    ]
    
    evaluator = LinkabilityEvaluator(ori=ori, 
                                     syn=syn, 
                                     control=control,
                                     n_attacks=num_link_attacks,
                                     aux_cols=aux_cols,
                                     n_neighbors=num_neighbors_linkability)
    
    evaluator.evaluate(n_jobs=-2)  # n_jobs follow joblib convention. -1 = all cores, -2 = all execept one
    lrisk = evaluator.risk()
    print(lrisk)
    lrisk_val = lrisk.value 
    ci_from = lrisk.ci[0] 
    ci_to = lrisk.ci[1]
    
    lrisk_score = 100 - 100 * lrisk_val
    lci_from = 100 * (1-ci_from)
    lci_to = 100 * (1-ci_to)
    status.update(label = ":link: Linkability: "+str(round(lrisk_score,2)), state='running',expanded=False)
    
    # Inference
    status.update(label = "Measuring Inference Risk...", state='running',expanded=False) 
    
    # If user has changed the dataset targets or updated the session state
    # use the selected columns for aux_cols
    if st.session_state['auxiliary_columns1'] is not None and st.session_state['auxiliary_columns2'] is not None:
        aux_cols = [
            st.session_state['auxiliary_columns1'],
            st.session_state['auxiliary_columns2']
        ]
    else:
        aux_cols = [
            ['type_employer', 'education', 'hr_per_week', 'capital_loss', 'capital_gain'],
            [ 'race', 'sex', 'fnlwgt', 'age', 'country']
        ]
    columns = ori.columns
    results = []
    
    for secret in columns:
        
        aux_cols = [col for col in columns if col != secret]
        
        evaluator = InferenceEvaluator(ori=ori, 
                                       syn=syn, 
                                       control=control,
                                       aux_cols=aux_cols,
                                       secret=secret,
                                       n_attacks=1000)
        evaluator.evaluate(n_jobs=-2)
        results.append((secret, evaluator.results()))
    
    irisk = evaluator.risk()
    print(irisk)
    irisk_val = irisk.value 
    ci_from = irisk.ci[0] 
    ci_to = irisk.ci[1]
    irisk_score = 100 - 100 * irisk_val
    ici_from = 100 * (1-ci_from)
    ici_to = 100 * (1-ci_to)
    status.update(label = ":crystal_ball: Inference: "+str(round(irisk_score,2)), state='running',expanded=False)
    return srisk_score, sci_to, lrisk_score, lci_to, irisk_score, ici_to


# Session variable
if 'is_settings_expanded' not in st.session_state:
    st.session_state['is_settings_expanded'] = True
if 'is_score_expanded' not in st.session_state:
    st.session_state['is_score_expanded'] = True
if 'num_sout_attacks' not in st.session_state:
    st.session_state['num_sout_attacks'] = 500
if 'num_link_attacks' not in st.session_state:
    st.session_state['num_link_attacks'] = 2000
if 'num_neighbors_linkability' not in st.session_state:
    st.session_state['num_neighbors_linkability'] = 10
if 'auxiliary_columns1' not in st.session_state:
    st.session_state['auxiliary_columns1'] = None
if 'auxiliary_columns2' not in st.session_state:
    st.session_state['auxiliary_columns2'] = None

st.set_page_config(
    page_title="Anonymeter",
    page_icon="🕵🏽‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("**Analyze Synthetic Data Risk with Anonymeter**")

header1, headera, header2 = st.columns([9,5,20])        
bucket_url = "https://storage.googleapis.com/statice-public/anonymeter-datasets/"

# Tabs!
data, sout, link, infer, more = st.tabs([":bar_chart: Datasets", 
                                ":dna: Singling Out",
                                ":link: Linkability",
                                ":crystal_ball: Inference",
                                ":books: More Info"])
with more:
    st.markdown(f"**_Anonymeter_** contains privacy evaluators to measure the risks of singling out, linkability, and inference attacks that may be carried out against a synthetic dataset."
                "\n These risks are the three key indicators of factual anonymization according to the [European General Data Protection Regulation (GDPR)](https://gdpr-info.eu/). ")
    st.markdown("For more details, please refer to [M. Giomi et al. 2022](https://petsymposium.org/popets/2023/popets-2023-0055.php).")
    st.markdown(f"View the Anonymeter source code on [Github](https://github.com/statice/anonymeter).")
with header1:
        
    with st.form("analysis_form"):
        # Every form must have a submit button.
        submitted = st.form_submit_button(":rocket: Analyze All")

with data:

    # Checkbox to use custom data
    use_own_data = st.toggle("Use my own data")

    if use_own_data:
        st.write("Upload your original, synthetic, and control datasets:")
        ori_file = st.file_uploader("Upload Original Data (CSV)", type="csv", key="ori")
        syn_file = st.file_uploader("Upload Synthetic Data (CSV)", type="csv", key="syn")
        control_file = st.file_uploader("Upload Control Data (CSV)", type="csv", key="control")

        if ori_file and syn_file and control_file:
            ori = pd.read_csv(ori_file)
            syn = pd.read_csv(syn_file)
            control = pd.read_csv(control_file)
        else:
            st.warning("Please upload all three datasets to proceed.")
            st.stop()
    else:
        ori = pd.read_csv(os.path.join(bucket_url, "adults_train.csv"))
        syn = pd.read_csv(os.path.join(bucket_url, "adults_syn_ctgan.csv"))
        control = pd.read_csv(os.path.join(bucket_url, "adults_control.csv"))
    
    
    dcol1, dcol2, dcol3 = st.columns(3)
    with dcol1:
        with st.expander("Original Dataset"):
            headers("Original Dataset",f"Training data is the original dataset, which is used to train the generative model.")
            st.dataframe(dfe(ori))
    with dcol2:
        with st.expander("Synthetic Dataset"):
            headers("Synthetic Dataset",f"Generated data is the synthetic dataset, which is generated by the generative model.")
            st.dataframe(dfe(syn))
    with dcol3:
        with st.expander("Control Dataset"):
            headers("Control Dataset",f"Lastly, the control dataset acts as a holdout group to validate the results.")
            st.dataframe(dfe(control))

with sout:
    st.markdown(f"## Measuring the Singling Out Risk\n\n"
                "The `SinglingOutEvaluator` measures synthetic data's exposure of combinations of attributes that single out records in the training data."
                "\n##### NOTE:\n\n"
                "The `SingingOutEvaluator` can sometimes raise an error. This happens when not enough singling out queries are found. Increasing the number of attacks with the slider below will make this condition less frequent and the evaluation more robust, although much slower.")
    st.divider()
    
    scol1, scol2 = st.columns(2)
    scol1.markdown("### Assess\n\nIn this example, we evaluate the susceptibility of the synthetic data to `univariate` singling out attacks, which try to find unique values of some attribute to single out an individual.\n\n")
    scol1.divider()
    with scol1.form("Singling Out Settings"):
        num_sout_attacks = st.slider(
                "**Number of Singling Out Attacks to Run**",
                min_value=100,
                max_value=1000,
                value=500,
                step=100,
                help="Use this to enter the number of Singling Out attacks")
        st.session_state['num_sout_attacks'] = num_sout_attacks
        sout_submitted = st.form_submit_button(":dna: Analyze Singling Out Risk")
    if sout_submitted:
        
        with scol2.status("Measuring Singling Out Risk...", expanded=False) as status:
            evaluator = SinglingOutEvaluator(ori=ori, 
                                             syn=syn, 
                                             control=control,
                                             n_attacks=num_sout_attacks)
            
            try:
                evaluator.evaluate(mode='univariate')
                srisk = evaluator.risk()
                print(srisk)
                srisk_val = srisk.value 
                ci_from = srisk.ci[0] 
                ci_to = srisk.ci[1]
    
                srisk_score = 100 - 100 * srisk_val
                sci_from = 100 * (1-ci_from)
                sci_to = 100 * (1-ci_to)
    
                st.metric("Singling Out Score", str(round(srisk_score,2))+' %', str(round(sci_to,2))+' %', delta_color="off")
                header2.metric("Singling Out Score", str(round(srisk_score,2))+' %', str(round(sci_to,2))+' %', delta_color="off")
                st.markdown(f"The risk estimate is accompanied by a confidence interval (at 95% level by default) which accounts for the finite number of attacks specified with the slider.")
            
            except RuntimeError as ex: 
                header2.error(f"Singling out evaluation failed with {ex}. Please re-run the analysis."
                      "For more stable results increase `n_attacks`. Note that this will "
                      "make the evaluation slower.")
                status.update(label=f"Singling out evaluation failed with {ex}. Please re-run the analysis."
                      "For more stable results increase `n_attacks`. Note that this will "
                      "make the evaluation slower.", state='error',expanded=False) 
            
            n_queries = 3
    
            sout_attacks = evaluator.queries()[:n_queries]
    
            headers(":crossed_swords: Attacks",
                f"Using the `queries()` method, we can see what kind of singling out queries (i.e. the *guesses*) the attacker has come up with."
                "\n\nAs visible it was able to pick up the `fnlwgt` has many (~63%) unique integer values  and that it can provide a powerful handle for singling out."
                "\n\nThis should result in a singling out risk which is *compatible* within the confidence level with a few percentage points."
                )
            
            q = 0
            while q < n_queries:
                st.write(sout_attacks[q])
                q=q+1

            if srisk_score and sci_from and sci_to:
                status.update(label = ":dna: Singling Out: "+str(round(srisk_score,2)), state='complete',expanded=True)
            


with link:
    
    st.markdown(f"## Measuring the Linkability Risk\n\n"
                "The `LinkabilityEvaluator` allows one to know how much the synthetic data will help an adversary who tries to link two other datasets based on a subset of attributes.\n\n"
                "For example, suppose that the adversary finds dataset A containing, among other fields, information about the profession and education of people, and dataset B containing some demographic and health related information. Can the attacker use the synthetic dataset to link these two datasets?\n\n"
                "To run the `LinkabilityEvaluator` one needs to specify which columns of auxiliary information are available to the attacker, and how they are distributed between the two datasets A and B. This is done using the `aux_cols` parameter."
                )
    st.divider()
    lcol1, lcol2 = st.columns(2)
    lcol1.markdown("### Assess\n\nSet the parameters for the linkability evaluation.")
    lcol1.divider()
    with lcol1.form("Linkability Settings"):
        num_link_attacks = st.slider(
            "**Number of Linkability Attacks to Run**",
            min_value=100,
            max_value=4000,
            value=2000,
            step=100,
            help="Use this to enter the number of Linkability attacks")
        st.session_state['num_link_attacks'] = num_link_attacks

        num_neighbors_linkability = st.slider(
            "**Number of Neighbors Identified by Linking**",
            min_value=2,
            max_value=20,
            value=10,
            step=1,
            help="Use this to enter the number of Neighbors for Linkability attacks")
        st.session_state['num_neighbors_linkability'] = num_neighbors_linkability

        # Generate list of shared columns in case the user wants to select them
        shared_columns = list(set(ori.columns).intersection(set(syn.columns)))

        auxiliary_columns1 = st.multiselect(
            'Select 1st group of Auxiliary Columns for Linkability Evaluation',
            shared_columns,
            default=['type_employer', 'education', 'hr_per_week', 'capital_loss', 'capital_gain']
        )
        st.session_state['auxiliary_columns1'] = auxiliary_columns1

        auxiliary_columns2 = st.multiselect(
            'Select 2nd group of Auxiliary Columns for Linkability Evaluation',
            shared_columns,
            default=['race', 'sex', 'fnlwgt', 'age', 'country']
        )
        st.session_state['auxiliary_columns2'] = auxiliary_columns2

        link_submitted = st.form_submit_button(":link: Analyze Linkablity Risk")
    if link_submitted:
        with lcol2.status("Measuring Linkability Risk...", expanded=False) as status:
            aux_cols = [
                auxiliary_columns1,
                auxiliary_columns2
            ]
            
            evaluator = LinkabilityEvaluator(ori=ori, 
                                             syn=syn, 
                                             control=control,
                                             n_attacks=num_link_attacks,
                                             aux_cols=aux_cols,
                                             n_neighbors=num_neighbors_linkability)
            
            evaluator.evaluate(n_jobs=-2)  # n_jobs follow joblib convention. -1 = all cores, -2 = all execept one
            lrisk = evaluator.risk()
    
            print(lrisk)
            lrisk_val = lrisk.value 
            ci_from = lrisk.ci[0] 
            ci_to = lrisk.ci[1]
            
            lrisk_score = 100 - 100 * lrisk_val
            lci_from = 100 * (1-ci_from)
            lci_to = 100 * (1-ci_to)
            
            st.metric(":link: Linkability", str(round(lrisk_score,2))+' %', str(round(lci_to))+' %', delta_color="off")
            header2.metric(":link: Linkability", str(round(lrisk_score,2))+' %', str(round(lci_to))+' %', delta_color="off")
            st.markdown(f"The risk estimate is accompanied by a confidence interval (at 95% level by default) which accounts for the finite number of attacks specified with the slider.")
            
            if lrisk_score and lci_from and lci_to:
                    status.update(label = ":link: Linkability: "+str(round(lrisk_score,2)), state='complete',expanded=False)
with infer:
    st.markdown(f"## Measuring the Inference Risk\n\n"
                "Finally, `Anonymeter` allows to measure the inference risk. It does so by measuring the success of an attacker that tries to discover the value of some secret attribute for a set of target records on which some auxiliary knowledge is available.\n\n"
                "Similar to the case of the `LinkabilityEvaluator`, the main parameter here is `aux_cols` which specify what the attacker knows about its target, i.e. which columns are known to the attacker. By selecting the `secret` column, one can identify which attributes, alone or in combinations, exhibit the largest risks and thereby expose a lot of information on the original data.\n\n"
                "In the following snippet we will measure the inference risk for each column individually, using all the other columns as auxiliary information to model a very knowledgeable attacker."
                )
    st.divider()
    icol1, icol2 = st.columns(2)
    icol1.markdown("\n\n ### Assess \n\nThe Anonymeter's inference risk assessment assumes that the attacker is very well informed, meaning all `aux_cols` are evaluated. As such, no parameters need to be specified, and we can run the evaluation right away.")
    icol1.divider()
    with icol1.form("Inference Settings"):
        infer_submitted = st.form_submit_button(":crystal_ball: Analyze Inference Risk")
    if infer_submitted:
        with icol2.status("Measuring Inference Risk...", expanded=False) as status:
            
            aux_cols = [
                auxiliary_columns1,
                auxiliary_columns2
            ]
            columns = ori.columns
            results = []
            
            for secret in columns:
                
                aux_cols = [col for col in columns if col != secret]
                
                evaluator = InferenceEvaluator(ori=ori, 
                                               syn=syn, 
                                               control=control,
                                               aux_cols=aux_cols,
                                               secret=secret,
                                               n_attacks=1000)
                evaluator.evaluate(n_jobs=-2)
                results.append((secret, evaluator.results()))
            
            irisk = evaluator.risk()
            print(irisk)
            irisk_val = irisk.value 
            ci_from = irisk.ci[0] 
            ci_to = irisk.ci[1]
            
            irisk_score = 100 - 100 * irisk_val
            ici_from = 100 * (1-ci_from)
            ici_to = 100 * (1-ci_to)
            
            st.metric(":crystal_ball: Inference", str(round(irisk_score,2))+' %', str(round(ici_to))+' %', delta_color="off")
            header2.metric(":crystal_ball: Inference", str(round(irisk_score,2))+' %', str(round(ici_to))+' %', delta_color="off")
            st.markdown(f"The risk estimate is accompanied by a confidence interval (at 95% level by default) which accounts for the finite number of attacks specified with the slider.")

            fig, ax = plt.subplots()
            
            risks = [res[1].risk().value for res in results]
            columns = [res[0] for res in results]
            
            ax.bar(x=columns, height=risks, alpha=0.5, color='blue', ecolor='black', capsize=10)
        
            plt.xticks(rotation=45, ha='right')
            ax.set_ylabel("Measured Inference Risk")
            _ = ax.set_xlabel("Secret Column")
            ax.xaxis.label.set_color('black')
            ax.yaxis.label.set_color('black')
    
            st.pyplot(fig)

            if irisk_score and ici_from and ici_to:
                status.update(label = ":crystal_ball: Inference Risk: "+str(round(irisk_score,2)), state='complete',expanded=True)
with header2:
    if submitted:
        with st.status("Measuring Holistic Risk Scores...", expanded=False) as status:
            analyzed = analyze_all(ori,
                                   syn,
                                   control,
                                   num_sout_attacks,
                                   num_link_attacks,
                                   num_neighbors_linkability, 
                                   auxiliary_columns1, 
                                   auxiliary_columns2
                                )
            col1, col2, col3 = st.columns(3)
            st.write("*Confidence indicator (CI) in grey")
            col1.metric(":dna: Singling Out", str(round(analyzed[0],2))+' %', str(round(analyzed[1],2))+' %', delta_color="off")
            col2.metric(":link: Linkability", str(round(analyzed[2],2))+' %', str(round(analyzed[3],2))+' %', delta_color="off")
            col3.metric(":crystal_ball: Inference", str(round(analyzed[4],2))+' %', str(round(analyzed[5],2))+' %', delta_color="off")
            status.update(label = "Analysis Complete", state='complete',expanded=True)