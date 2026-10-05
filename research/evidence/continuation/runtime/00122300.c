
int * FUN_00122300(long param_1,int *param_2,long param_3,long param_4)

{
  ushort uVar1;
  int iVar2;
  int iVar3;
  undefined4 *puVar4;
  int iVar5;
  undefined2 *puVar6;
  uint uVar7;
  int *piVar8;
  uint uVar9;
  int iVar10;
  int *piVar11;
  ushort *puVar12;
  int *piVar13;
  int iVar14;
  int *piVar15;
  
  if (param_1 == -1) {
                    /* WARNING: Subroutine does not return */
    FUN_00105888(0x2528f8,0x4d,0x252918);
  }
  if ((param_3 != 0) && (param_4 != 0)) {
    *(int *)param_3 = 0;
    *(int *)param_4 = 0;
  }
  iVar3 = FUN_001213d8();
  if (-1 < *(int *)(iVar3 + 0x14)) {
    iVar14 = 0xff;
    puVar4 = &DAT_002cb70c;
    do {
      iVar14 = iVar14 + -1;
      *puVar4 = 0;
      puVar4 = puVar4 + -1;
    } while (-1 < iVar14);
    iVar14 = 0;
    uVar9 = 0;
    if (*(char *)(iVar3 + 0x14) != '\0') {
      puVar12 = *(ushort **)(iVar3 + 0x50);
      do {
        iVar14 = iVar14 + 1;
        (&DAT_002cb310)[*puVar12] = (&DAT_002cb310)[*puVar12] + 1;
        uVar9 = (uint)*(byte *)(iVar3 + 0x14);
        puVar12 = puVar12 + 2;
      } while (iVar14 < (int)uVar9);
    }
    iVar14 = 0;
    uVar7 = 0;
    if (*(char *)(iVar3 + 0x11) != '\0') {
      iVar10 = 0;
      do {
        iVar14 = iVar14 + 1;
        iVar5 = iVar10 + *(int *)(iVar3 + 0x54);
        *(uint *)(iVar5 + 4) = *(uint *)(iVar5 + 4) & 0xfffeffff;
        uVar7 = (uint)*(byte *)(iVar3 + 0x11);
        iVar10 = iVar10 + 0x2c;
      } while (iVar14 < (int)uVar7);
      uVar9 = (uint)*(byte *)(iVar3 + 0x14);
    }
    iVar14 = 0;
    if (uVar9 != 0) {
      iVar10 = 0;
      do {
        iVar14 = iVar14 + 1;
        iVar5 = iVar10 + *(int *)(iVar3 + 0x54);
        *(uint *)(iVar5 + 4) = *(uint *)(iVar5 + 4) | 0x10000;
        iVar10 = iVar10 + 0x2c;
      } while (iVar14 < (int)(uint)*(byte *)(iVar3 + 0x14));
      uVar7 = (uint)*(byte *)(iVar3 + 0x11);
    }
    iVar14 = 0;
    if (uVar7 != 0) {
      iVar5 = 0;
      iVar10 = *(int *)(iVar3 + 0x54);
      while( true ) {
        iVar14 = iVar14 + 1;
        iVar10 = iVar10 + iVar5;
        iVar5 = iVar5 + 0x2c;
        FUN_00123078(iVar10);
        if ((int)(uint)*(byte *)(iVar3 + 0x11) <= iVar14) break;
        iVar10 = *(int *)(iVar3 + 0x54);
      }
    }
    iVar10 = 0;
    piVar13 = &DAT_002cb310;
    iVar14 = 0;
    iVar5 = 0xff;
    do {
      iVar2 = *piVar13;
      piVar13 = piVar13 + 1;
      iVar5 = iVar5 + -1;
      if (iVar2 != 0) {
        iVar14 = iVar14 + 1;
      }
      iVar10 = iVar10 + iVar2;
    } while (-1 < iVar5);
    if (iVar14 == 0) {
      if (param_2 != (int *)0x0) {
        return param_2;
      }
    }
    else if (param_2 != (int *)0x0) {
      *(char *)(iVar3 + 0x15) = (char)iVar14;
      *(int **)(iVar3 + 0x34) = param_2;
      piVar11 = param_2 + iVar14 * 3;
      piVar15 = piVar11 + iVar10;
      piVar8 = &DAT_002cb310;
      iVar10 = 0;
      piVar13 = param_2;
      do {
        if (*piVar8 != 0) {
          *piVar13 = iVar10;
          piVar13[1] = 0;
          piVar13[2] = (int)piVar11;
          piVar13 = piVar13 + 3;
          piVar11 = piVar11 + *piVar8;
        }
        iVar10 = iVar10 + 1;
        piVar8 = piVar8 + 1;
      } while (iVar10 < 0x100);
      iVar10 = 0;
      piGpffff93cc = param_2;
      iGpffffaa20 = iVar14;
      if (*(char *)(iVar3 + 0x14) != '\0') {
        iVar14 = *(int *)(iVar3 + 0x50);
        while( true ) {
          iVar5 = iVar10 * 4;
          iVar10 = iVar10 + 1;
          puVar6 = (undefined2 *)(iVar5 + iVar14);
          uVar1 = puVar6[1];
          FUN_00123820(*puVar6,*(int *)(iVar3 + 0x54) + ((uint)uVar1 * 0xc - (uint)uVar1) * 4);
          if ((int)(uint)*(byte *)(iVar3 + 0x14) <= iVar10) break;
          iVar14 = *(int *)(iVar3 + 0x50);
        }
      }
      iVar14 = 0;
      if (*(char *)(iVar3 + 0x11) == '\0') {
        return piVar15;
      }
      iVar5 = 0;
      iVar10 = *(int *)(iVar3 + 0x54);
      while( true ) {
        iVar14 = iVar14 + 1;
        iVar10 = iVar10 + iVar5;
        iVar5 = iVar5 + 0x2c;
        FUN_00123758(iVar10);
        if ((int)(uint)*(byte *)(iVar3 + 0x11) <= iVar14) break;
        iVar10 = *(int *)(iVar3 + 0x54);
      }
      return piVar15;
    }
    param_2 = (int *)0x0;
    *(int *)param_3 = iVar14 * 0xc;
    *(int *)param_4 = iVar10 * 4;
  }
  return param_2;
}

