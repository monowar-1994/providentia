// #include <stdio.h>
// #include <malloc.h>
// #include <string.h>

static int sg_some_var;

void a_random_stuff(){
    return;
}

static void sumfunc(int a){
    printf("a is %d\n",a);
}

int main(int argc, char const *argv[])
{
    sg_some_var = 1;
    somefunc(argc);
    const char *filename = "/home/rashik/Documents/scripts/input.txt";
    FILE *fp;
    fp = fopen(filename, "r");
    if(fp == NULL){
        printf("Invalid file name.\n");
        return 0;
    }
    else{
        fclose(fp);
        // char *copied_file_name = (char *)malloc(sizeof(char)*strlen(filename) + 1);
        // strcpy(copied_file_name, filename);
        printf("Copied file name is: %s\n", copied_file_name);
    }

    return sg_some_var? 0:1;
}
