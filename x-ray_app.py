#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  1 20:14:48 2022

@author: maxwood
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


from pymatgen.ext.matproj import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.analysis import phase_diagram as phs
from statistics import median
import webbrowser
import scipy.stats as stats
import math

mpr = MPRester(st.secrets['MPKey'])



def xrd_maker(two_theta,height):
    mu = 0
    variance = .05
    sigma = math.sqrt(variance)
    x = np.linspace(-100, 100, 40001)
    y = stats.norm.pdf(x, mu, sigma)
    
    peak_x = np.around(x+two_theta,decimals = 2)
    peak_y = np.around(y*height,decimals = 4)
    return(peak_x,peak_y) 


def full_plot(struc):
    c = XRDCalculator()
    patt = c.get_pattern(struc)

    xs = np.around(patt.x,decimals = 2).reshape(-1)
    ys = np.around(patt.y,decimals = 2)

    full_profile_x = np.linspace(0,200, 40001)
    full_profile_y = np.zeros(40001).reshape(40001,1)

    i = 0
    for x in xs:
        y = ys[i]
        (peakx,peaky)=xrd_maker(x,y)
        start = np.where(peakx==0)[0][0]
        re_centered = np.concatenate((peaky[start:],np.zeros(start))).reshape(40001,1)
        full_profile_y = np.concatenate((full_profile_y,re_centered),axis = 1)
        i = i+1
        
    y_sum = np.sum(full_profile_y,axis = 1)
    y_final = y_sum[:18000]
    x_final = full_profile_x[:18000]
    return(x_final,y_final/178.4124)

st.write(
    """
#  X-Ray Diffraction Analyzer
Upload your powder XRD data and compare against phases in the Materials Project 
database to determine what phase your material is!
"""
)

user_xray = st.file_uploader('Diffraction Pattern (two theta, intensity)')
if user_xray is not None:

    df = pd.read_csv(user_xray, delim_whitespace=(True))
    x_ex = df.iloc[:, 0]
    y_ex = df.iloc[:, 1]
    y_max = y_ex.max()
    y_min = y_ex.min()
    y_med = median(y_ex)
    x_min = x_ex.min()
    x_max = x_ex.max()
    x_step = np.around(x_ex[1]-x_ex[0],decimals = 5)
    y_scaled = (y_ex-y_med)/(y_max-y_med)
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.plot(x_ex,y_scaled)
    plt.xlabel('2θ')
    plt.ylabel('Intensity (scaled)') 
    st.write(fig)

with st.sidebar:
    col1, col2 = st.columns(2)
    
    with col1:
        Element1 = st.text_input('Element 1')
    
    with col2:
        Element2 = st.text_input('Element 2')
    col3, col4 = st.columns(2)
    with col3:
        Element3 = st.text_input('Element 3')
    
    with col4:
        Element4 = st.text_input('Element 4')
    
    
    #Entries are the basic unit for thermodynamic and other analyses in pymatgen.
    #entries is a list of all the compounds that form from the elements specified below
    
    
    st.write('Elements Searched', Element1, Element2,Element3, Element4)
    
    if 'button_clicked' not in st.session_state:
        st.session_state.button_clicked = False
    
        
    def callback():
        st.session_state.button_clicked = True
    
    
    #call_entries = st.button('Get Possible Compounds!',on_click = callback)
    
    
    if (st.button('Query Materials Project!',on_click = callback)
        or st.session_state.button_clicked
        ):
        entries = mpr.get_entries_in_chemsys([Element1, Element2,Element3, Element4])
        #With entries, you can do many sophisticated analyses, like creating phase diagrams.
        pdi = PhaseDiagram(entries)
        stable = pdi.stable_entries
        v = np.ones(len(stable))
        structures = np.ones(len(stable))
        mpid = []
        structures = []
        patterns = []
        names = []
        i = 0
        for entry in stable:
            #v[i] = st.checkbox(entry.name)
            mpid.append(entry.entry_id)
            structures.append(mpr.get_structure_by_material_id(entry.entry_id))
            patterns.append(full_plot(structures[i]))
            i = i+1
            names.append(entry.name)
            st.write('I found '+str(entry.name)+' is stable')
            
        residuals = []
        residuals_abs = []
        residuals_summed = []
        y_theo = []
        i = 0
  
        for pattern in patterns:
            (x_patt,y_patt) = pattern
            a = np.where(x_patt==x_min)[0][0]
            d = np.where(x_patt==(x_min+x_step))[0][0]
            c = d-a
            b = np.where(x_patt==x_max)[0][0]+1

            x_comp = x_patt[a:b:c]
            y_comp = y_patt[a:b:c]
            y_theo.append(y_comp)
            residuals.append(y_scaled-y_comp)
            residuals_abs.append(np.abs(y_scaled-y_comp))
            residuals_summed.append(residuals_abs[i].sum())
            i =i+1
            
if st.session_state.button_clicked:
    best_fit = np.argmin(np.abs(np.array(residuals_summed)))
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    #ax.plot(x_ex,y_scaled)
    ax.plot(x_ex,y_scaled+1.2, label = 'Experimental Data')
    ax.plot(x_comp,y_theo[best_fit], label = str(names[best_fit]+' Theo Pattern'))
    ax.plot(x_comp,residuals[best_fit]-0.2, label = 'Residuals')
    ax.legend()


    plt.xlabel('2θ')
    plt.ylabel('Intensity (scaled)') 
    st.write(fig)
    st.write('The best fit for your data was ' + names[best_fit])
    

    url = 'https://materialsproject.org/materials/'+str(mpid[best_fit])
    
    if st.button('Learn More About '+str(names[best_fit])):
        webbrowser.open_new_tab(url)
    

st.write(""" ##### Made by Max Wood""")
        