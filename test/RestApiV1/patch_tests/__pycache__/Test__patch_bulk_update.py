o
    �e�  �                   @   sv   d Z ddlmZ e�� ZddlZddlZddlZddlZddl	m
Z
mZmZ G dd� dej�Zedkr9e��  dS dS )a�  
test/RestApiV1/Test__patch_hwitem.py
Copyright (c) 2023 Regents of the University of Minnesota
Author: Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy

Tests: 
    post_bulk_add()
        (using REST API: POST /api/v1/component-types/{part_type_id}/bulk-add)
    patch_bulk_update() 
        (using REST API: PATCH /api/v1/component-types/{part_type_id}/bulk-update)
    get_component_type()
        (using REST API: /api/v1/component-types/{part_type_id})
�    )�configN)�post_bulk_add�patch_bulk_update�get_component_typec                   @   s.   e Zd Zdd� Zdd� Ze�d�dd� �ZdS )	�Test__patch_bulk_updatec                 C   s
   d| _ d S )Ni   )�maxDiff��self� r
   �d/Users/urbas/Documents/GitHub/DUNE-HWDB-Python/test/RestApiV1/patch_tests/Test__patch_bulk_update.py�setUp!   s   
zTest__patch_bulk_update.setUpc                 C   s   d S )Nr
   r   r
   r
   r   �tearDown$   s   z Test__patch_bulk_update.tearDownz throws internal server error 500c           	   
   C   s8  d}t �d|� d�� z�d}dd|iddd	d
id	did�}t �d|� d�� t||�}t �d|� �� | �|d d� |d d d }|d d d }t �d|� �� t �d|� �� dt�dd�d��}dd	didd	di||ddid�d	didd	di||ddid�gi}t||�}t �d|� �� | �|d d� t �d |� �� t|�}t �d!|� �� | �|d d� | �|d d |� | �|d d" |� t|�}t �d!|� �� | �|d d� | �|d d |� | �|d d" |� W n t�y } zt �	d#|� d�� t �|� |�d }~ww t �d$|� d�� d S )%Nr   z[TEST �]�Z00100300001zHere are some comments�part_type_id�   �US�id�   �   )�comments�component_type�count�country_code�institution�manufacturerz&Posting bulk components: part_type_id=z, zResponse from post: �status�OK�datar   �part_id�   z#New component type result: part_id=�SNl   �� �08XzPatched component types�ColorZBlue)�batchr   r   r   �serial_number�specifications�RedzResponse from patch: z4getting component type for comparison: part_type_id=zresult: r%   z[FAIL z[PASS )
�logger�infor   �assertEqual�random�randintr   r   �AssertionError�error)	r	   �testnamer   r   �resp�part_id1�part_id2r%   �errr
   r
   r   �test_patch_bulk_update'   s�   ����
����������
"
��z.Test__patch_bulk_update.test_patch_bulk_updateN)�__name__�
__module__�__qualname__r   r   �unittest�skipr4   r
   r
   r
   r   r      s
    r   �__main__)�__doc__�Sisyphus.Configurationr   �	getLoggerr(   �os�jsonr8   r+   �Sisyphus.RestApiV1r   r   r   �TestCaser   r5   �mainr
   r
   r
   r   �<module>   s   t�