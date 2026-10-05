
uint FUN_00123908(int param_1,int *param_2)

{
  int iVar1;
  int iVar2;
  int *piVar3;
  int *piVar4;
  
  *(int **)(param_1 + 0x84) = param_2;
  iVar1 = *param_2;
  piVar4 = param_2 + 2;
  iVar2 = param_2[1];
  *(int **)(param_1 + 0x88) = piVar4;
  *(int *)(param_1 + 0xb4) = iVar2;
  piVar4 = piVar4 + iVar2;
  if (0 < iVar2) {
    piVar3 = *(int **)(param_1 + 0x88);
    do {
      iVar2 = iVar2 + -1;
      *piVar3 = *(int *)(param_1 + 0x84) + *piVar3;
      piVar3 = piVar3 + 1;
    } while (iVar2 != 0);
  }
  piVar3 = piVar4 + 1;
  iVar2 = *piVar4;
  *(int **)(param_1 + 0x8c) = piVar3;
  *(int *)(param_1 + 0xb8) = iVar2;
  piVar3 = piVar3 + iVar2;
  if (0 < iVar2) {
    piVar4 = *(int **)(param_1 + 0x8c);
    do {
      iVar2 = iVar2 + -1;
      *piVar4 = *(int *)(param_1 + 0x84) + *piVar4;
      piVar4 = piVar4 + 1;
    } while (iVar2 != 0);
  }
  piVar4 = piVar3 + 1;
  iVar2 = *piVar3;
  *(int **)(param_1 + 0x9c) = piVar4;
  *(int *)(param_1 + 200) = iVar2;
  piVar4 = piVar4 + iVar2;
  if (0 < iVar2) {
    piVar3 = *(int **)(param_1 + 0x9c);
    do {
      iVar2 = iVar2 + -1;
      *piVar3 = *(int *)(param_1 + 0x84) + *piVar3;
      piVar3 = piVar3 + 1;
    } while (iVar2 != 0);
  }
  piVar3 = piVar4 + 1;
  iVar2 = *piVar4;
  *(int **)(param_1 + 0x90) = piVar3;
  *(int *)(param_1 + 0xbc) = iVar2;
  piVar3 = piVar3 + iVar2;
  if (0 < iVar2) {
    piVar4 = *(int **)(param_1 + 0x90);
    do {
      iVar2 = iVar2 + -1;
      *piVar4 = *(int *)(param_1 + 0x84) + *piVar4;
      piVar4 = piVar4 + 1;
    } while (iVar2 != 0);
  }
  piVar4 = piVar3 + 1;
  iVar2 = *piVar3;
  *(int **)(param_1 + 0x94) = piVar4;
  *(int *)(param_1 + 0xc0) = iVar2;
  piVar4 = piVar4 + iVar2;
  if (0 < iVar2) {
    piVar3 = *(int **)(param_1 + 0x94);
    do {
      iVar2 = iVar2 + -1;
      *piVar3 = *(int *)(param_1 + 0x84) + *piVar3;
      piVar3 = piVar3 + 1;
    } while (iVar2 != 0);
  }
  piVar3 = piVar4 + 1;
  iVar2 = *piVar4;
  *(int **)(param_1 + 0x98) = piVar3;
  *(int *)(param_1 + 0xc4) = iVar2;
  piVar3 = piVar3 + iVar2;
  if (0 < iVar2) {
    piVar4 = *(int **)(param_1 + 0x98);
    do {
      iVar2 = iVar2 + -1;
      *piVar4 = *(int *)(param_1 + 0x84) + *piVar4;
      piVar4 = piVar4 + 1;
    } while (iVar2 != 0);
  }
  piVar4 = piVar3 + 1;
  iVar2 = *piVar3;
  *(int **)(param_1 + 0xa0) = piVar4;
  *(int *)(param_1 + 0xcc) = iVar2;
  piVar4 = piVar4 + iVar2;
  if (0 < iVar2) {
    piVar3 = *(int **)(param_1 + 0xa0);
    do {
      iVar2 = iVar2 + -1;
      *piVar3 = *(int *)(param_1 + 0x84) + *piVar3;
      piVar3 = piVar3 + 1;
    } while (iVar2 != 0);
  }
  piVar3 = piVar4 + 1;
  iVar2 = *piVar4;
  *(int **)(param_1 + 0xa4) = piVar3;
  *(int *)(param_1 + 0xd0) = iVar2;
  piVar3 = piVar3 + iVar2;
  if (0 < iVar2) {
    piVar4 = *(int **)(param_1 + 0xa4);
    do {
      iVar2 = iVar2 + -1;
      *piVar4 = *(int *)(param_1 + 0x84) + *piVar4;
      piVar4 = piVar4 + 1;
    } while (iVar2 != 0);
  }
  piVar4 = piVar3 + 1;
  iVar2 = *piVar3;
  *(int **)(param_1 + 0xa8) = piVar4;
  *(int *)(param_1 + 0xd4) = iVar2;
  piVar4 = piVar4 + iVar2;
  if (0 < iVar2) {
    piVar3 = *(int **)(param_1 + 0xa8);
    do {
      iVar2 = iVar2 + -1;
      *piVar3 = *(int *)(param_1 + 0x84) + *piVar3;
      piVar3 = piVar3 + 1;
    } while (iVar2 != 0);
  }
  piVar3 = piVar4 + 1;
  iVar2 = *piVar4;
  *(int **)(param_1 + 0xac) = piVar3;
  *(int *)(param_1 + 0xd8) = iVar2;
  if (0 < iVar2) {
    do {
      iVar2 = iVar2 + -1;
      *piVar3 = *(int *)(param_1 + 0x84) + *piVar3;
      piVar3 = piVar3 + 1;
    } while (iVar2 != 0);
  }
  return (int)param_2 + iVar1 + 0xf & 0xfffffff0;
}

