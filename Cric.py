import random


team={"Player "+str(i):None for i in range(1,12)}
comp={"Computer "+str(i):None for i in range(1,12)}
def runadd(st,nst,bat,teamScore):
    team["Player "+str(st)]+=bat
    if bat%2!=0:
        st,nst=nst,st
    teamScore+=bat
    return st,nst,teamScore

def compadd(st,nst,bat,compScore):
    comp["Computer "+str(st)]+=bat
    if bat%2!=0:
        st,nst=nst,st
    compScore+=bat
    return st,nst,compScore


def selectbat(pre,pst,st,nst):
    if not st and not nst:
        team[pre+str(1)]=0
        team[pre+str(2)]=0
        return 1,2
    elif not st:
        st=max(pst,nst)+1
        team[pre+str(st)]=0
        return st,nst
    
def compbat(pre,pst,st,nst):
    if not st and not nst:
        comp[pre+str(1)]=0
        comp[pre+str(2)]=0
        return 1,2
    elif not st:
        st=max(pst,nst)+1
        comp[pre+str(st)]=0
        return st,nst
    

def bowling(st,nst,compScore,compwicket):
    try:
        bowl=int(input("Bowling : "))
        if bowl<1 or bowl>6:
            print("Invalid Input")
            bowl=random.randint(1,6)
            print("We selected \nBowling : ",bowl)
    except:
        bowl=random.randint(1,6)
        print("We selected \nBowling : ",bowl)        
    bat=random.randint(1,6)
    print("Batting : ",bat)
    if bat==bowl:
        compwicket+=1
        print("Computer "+str(st)+" is out.")
        if compwicket<10:
            st,nst=compbat("Computer ",st,None,nst)
            print("New Batsman is Computer "+str(st))
    else:
        st,nst,compScore=compadd(st,nst,bat,compScore)
    return st,nst,compScore,compwicket

def batting(st,nst,teamScore,teamwicket):
    try:
        bat=int(input("Player "+str(st)+" Batting : "))
        if bat>6 or bat<1:
            print("Invalid Input")
            bat=random.randint(1,6)
            print("We selected \nBatting : ",bat)
    except:
        bat=random.randint(1,6)
        print("We selected \nBatting : ",bat)
    bowl=random.randint(1,6)
    print("Bowling : ",bowl)
    if bat==bowl:
        teamwicket+=1
        print("Player "+str(st)+" is out.")
        if teamwicket<10:
            st,nst=selectbat("Player ",st,None,nst)
            print("New Batsman is Player "+str(st))
    else:
        st,nst,teamScore=runadd(st,nst,bat,teamScore)
    return st,nst,teamScore,teamwicket


def cointoss(inp):
    win=random.choice(["heads","tails"])
    if inp.lower()==win:
        return True
    else:
        return False
    
def tossdecision(inp):
    result=cointoss(inp)
    choice=None
    if result:
        retry=0
        print("You Won Toss")
        choice=input("Select (Batting / Bowling) : ").lower()
        while choice not in ["batting","bowling"]:
            if retry==3:
                print("Too many Invalid Inputs")
                print("You are batting first")
                choice="batting"
                break
            print("Invalid Input")
            choice=input("Select (Batting / Bowling) : ").lower()
            retry+=1
        return choice
            
    else:
        choice=random.choice(["batting","bowling"])
        print("Computer Won Toss and Decided to ",choice.capitalize()," first.")
        return "bowling" if choice=="batting" else "batting"

def score(team):
    print("Your Scorecard")
    print("Player \t    Runs")
    for k,v in team.items():
        if v is None:
            print(k," : Did not bat")
        else:
            print(k," : ",v)
    return

def batmechanism(teamScore,
    Target,
    teamwicket,):
    bowls=0
    st,nst=selectbat("Player ",None,None,None)
    while bowls<120 and teamwicket<10:
        bowls+=1
        rst,rnst,teamScore,teamwicket=batting(st,nst,teamScore,teamwicket)
        st,nst=rst,rnst
        if Target:
            if teamScore>Target:
                break
    if Target:
        print("Your total Score : ",teamScore)
        if teamScore>Target:
            print("You Won the match by ",10-teamwicket,"wickets.")
            score(team)
            return
        elif teamScore<Target:
            print("Computer Won the match by ",Target-teamScore," runs.")
            score(team)
        else:
            print("Match Tied")
            score(team)
            return
    else:
        Target=teamScore+1
        print("Your total Score : ",teamScore)
        print("Total to defend : ",Target,"\n")
        score(team)
        return Target
    
def bowlmechanism(compScore,Target,compwicket):
    bowls=0
    st,nst=compbat("Computer ",None,None,None)
    while bowls<120 and compwicket<10:
        bowls+=1
        rst,rnst,compScore,compwicket=bowling(st,nst,compScore,compwicket)
        st,nst=rst,rnst
        if Target:
            if compScore>Target:
                break
    if Target:
        print("Computer total Score : ",compScore)
        if compScore>Target:
            print("Computer Won the match by ",10-compwicket,"wickets.")
            score(comp)
            return
        elif compScore<Target:
            score(comp)
            print("You Won the match by ",Target-compScore," runs.")
        else:
            print("Match Tied")
            score(comp)
            return
    else:
        Target=compScore+1
        print("Computer total Score : ",compScore)
        print("Total to Chase : ",Target,"\n")
        score(comp)
        return Target

def main():

    retry=0
    toss_inp=input("Enter (Heads / Tails) :").lower()
    while toss_inp not in ["heads","tails"]:
        if retry==3:
            print("Too Many Invalid Inputs")
            print("Your Schoice is Selected as Heads")
            toss_inp="heads"
            break
        print("Invalid Input")
        toss_inp=input("Enter (Heads / Tails) :").lower()
        retry+=1
    des=tossdecision(toss_inp)
    teamScore=0
    compScore=0
    Target=None
    teamwicket=0
    compwicket=0
    if des=="batting":
        Target=batmechanism(teamScore,Target,teamwicket)
        print("\n\nYour Bowling Starts\n")
        bowlmechanism(compScore,Target,compwicket)
        return
    else:
        Target=bowlmechanism(compScore,Target,compwicket)
        print("\n\nYour Batting Starts\n")
        batmechanism(teamScore,Target,teamwicket)
        return

main()
            
       