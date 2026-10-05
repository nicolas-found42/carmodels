
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/3d/3dsubobj.c:77 */

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
  ushort *puVar11;
  int *piVar12;
  int iVar13;
  int *piVar14;
  
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
    iVar13 = 0xff;
    puVar4 = &DAT_002cb70c;
    do {
      iVar13 = iVar13 + -1;
      *puVar4 = 0;
      puVar4 = puVar4 + -1;
    } while (-1 < iVar13);
    iVar13 = 0;
    uVar9 = 0;
    if (*(char *)(iVar3 + 0x14) != '\0') {
      puVar11 = *(ushort **)(iVar3 + 0x50);
      do {
        iVar13 = iVar13 + 1;
        (&DAT_002cb310)[*puVar11] = (&DAT_002cb310)[*puVar11] + 1;
        uVar9 = (uint)*(byte *)(iVar3 + 0x14);
        puVar11 = puVar11 + 2;
      } while (iVar13 < (int)uVar9);
    }
    iVar13 = 0;
    uVar7 = 0;
    if (*(char *)(iVar3 + 0x11) != '\0') {
      iVar10 = 0;
      do {
        iVar13 = iVar13 + 1;
        iVar5 = iVar10 + *(int *)(iVar3 + 0x54);
        *(uint *)(iVar5 + 4) = *(uint *)(iVar5 + 4) & 0xfffeffff;
        uVar7 = (uint)*(byte *)(iVar3 + 0x11);
        iVar10 = iVar10 + 0x2c;
      } while (iVar13 < (int)uVar7);
      uVar9 = (uint)*(byte *)(iVar3 + 0x14);
    }
    iVar13 = 0;
    if (uVar9 != 0) {
      iVar10 = 0;
      do {
        iVar13 = iVar13 + 1;
        iVar5 = iVar10 + *(int *)(iVar3 + 0x54);
        *(uint *)(iVar5 + 4) = *(uint *)(iVar5 + 4) | 0x10000;
        iVar10 = iVar10 + 0x2c;
      } while (iVar13 < (int)(uint)*(byte *)(iVar3 + 0x14));
      uVar7 = (uint)*(byte *)(iVar3 + 0x11);
    }
    iVar13 = 0;
    if (uVar7 != 0) {
      iVar5 = 0;
      iVar10 = *(int *)(iVar3 + 0x54);
      while( true ) {
        iVar13 = iVar13 + 1;
        iVar10 = iVar10 + iVar5;
        iVar5 = iVar5 + 0x2c;
        FUN_00123078(iVar10);
        if ((int)(uint)*(byte *)(iVar3 + 0x11) <= iVar13) break;
        iVar10 = *(int *)(iVar3 + 0x54);
      }
    }
    iVar10 = 0;
    piVar12 = &DAT_002cb310;
    iVar13 = 0;
    iVar5 = 0xff;
    do {
      iVar2 = *piVar12;
      piVar12 = piVar12 + 1;
      iVar5 = iVar5 + -1;
      if (iVar2 != 0) {
        iVar13 = iVar13 + 1;
      }
      iVar10 = iVar10 + iVar2;
    } while (-1 < iVar5);
    if (iVar13 == 0) {
      if (param_2 != (int *)0x0) {
        return param_2;
      }
    }
    else if (param_2 != (int *)0x0) {
      piRam0028f13c = param_2;
      iRam00290790 = iVar13;
      *(char *)(iVar3 + 0x15) = (char)iVar13;
      *(int **)(iVar3 + 0x34) = param_2;
      param_2 = param_2 + iVar13 * 3;
      piVar14 = param_2 + iVar10;
      piVar8 = &DAT_002cb310;
      iVar13 = 0;
      piVar12 = piRam0028f13c;
      do {
        if (*piVar8 != 0) {
          *piVar12 = iVar13;
          piVar12[1] = 0;
          piVar12[2] = (int)param_2;
          piVar12 = piVar12 + 3;
          param_2 = param_2 + *piVar8;
        }
        iVar13 = iVar13 + 1;
        piVar8 = piVar8 + 1;
      } while (iVar13 < 0x100);
      iVar13 = 0;
      if (*(char *)(iVar3 + 0x14) != '\0') {
        iVar10 = *(int *)(iVar3 + 0x50);
        while( true ) {
          iVar5 = iVar13 * 4;
          iVar13 = iVar13 + 1;
          puVar6 = (undefined2 *)(iVar5 + iVar10);
          uVar1 = puVar6[1];
          FUN_00123820(*puVar6,*(int *)(iVar3 + 0x54) + ((uint)uVar1 * 0xc - (uint)uVar1) * 4);
          if ((int)(uint)*(byte *)(iVar3 + 0x14) <= iVar13) break;
          iVar10 = *(int *)(iVar3 + 0x50);
        }
      }
      iVar13 = 0;
      if (*(char *)(iVar3 + 0x11) == '\0') {
        return piVar14;
      }
      iVar5 = 0;
      iVar10 = *(int *)(iVar3 + 0x54);
      while( true ) {
        iVar13 = iVar13 + 1;
        iVar10 = iVar10 + iVar5;
        iVar5 = iVar5 + 0x2c;
        FUN_00123758(iVar10);
        if ((int)(uint)*(byte *)(iVar3 + 0x11) <= iVar13) break;
        iVar10 = *(int *)(iVar3 + 0x54);
      }
      return piVar14;
    }
    param_2 = (int *)0x0;
    *(int *)param_3 = iVar13 * 0xc;
    *(int *)param_4 = iVar10 * 4;
  }
  return param_2;
}

