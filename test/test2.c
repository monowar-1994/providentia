void main(){
    int a = 0;
    int b = -1;
    int x = -10;
    A();
    B();
    
    if(a>0){
        printf("This is if true block.\n");
        
        if(b>0){
            printf("I have no clue\n");
            
            if(x>-9){
                C();
            }
            else{
                D();
            }
        }
        
    }
    else{
        exit(0);
    }
    return 0;
}