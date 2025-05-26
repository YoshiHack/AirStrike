from art import * 
from termcolor import colored


def banner(message):
    art = text2art(message)
    return(colored(art, 'red'))



def team():
    print(
    "    __________________________________________________________________________ \n"
    ">  |                                                                          |\n"
    ">  | Utility by Mahmoud Sadder,Ahmad Alkadi,Mustafa Majdalawi and Khalid Safi |\n"
    ">  |__________________________________________________________________________|\n")
