
/* WARNING: Removing unreachable block (ram,0x00123fa8) */

void FUN_00123f18(undefined8 param_1)

{
  bool bVar1;
  ushort uVar2;
  byte bVar3;
  int iVar4;
  int iVar5;
  undefined4 uVar6;
  undefined8 uVar7;
  int *piVar8;
  uint *puVar9;
  int iVar10;
  int *piVar11;
  int iVar12;
  int iVar13;
  uint uVar14;
  int iVar15;
  int iVar16;
  int iVar17;
  int aiStack_450 [256];
  undefined1 auStack_50 [16];
  
  iVar16 = (int)param_1;
  iVar4 = FUN_0021b6e0(*(undefined4 *)(iVar16 + 4));
  iVar5 = FUN_001213d8(*(undefined4 *)(iVar16 + 4));
  uVar2 = *(ushort *)(iVar16 + 100);
  uVar14 = (uint)*(byte *)(iVar5 + 0xe);
  iVar17 = 0;
  if (uVar14 != 0) {
    iVar10 = *(int *)(iVar4 + 0xf4);
    piVar8 = *(int **)(iVar5 + 0x1c);
    do {
      iVar15 = *piVar8;
      puVar9 = (uint *)(iVar15 * 8 + iVar10);
      if (((*puVar9 & 0x1000) != 0) && (*(char *)((int)puVar9 + 2) != '\0')) {
        iVar13 = 0;
        if (*(byte *)((int)puVar9 + 3) == uVar2) {
          iVar13 = *(int *)(iVar4 + 0xec);
          uVar14 = puVar9[1];
        }
        else {
          do {
            iVar13 = iVar13 + 1;
            iVar12 = (iVar15 + iVar13) * 8 + iVar10;
            if ((int)(uint)*(byte *)(iVar15 * 8 + iVar10 + 2) < iVar13) goto LAB_00124014;
          } while (*(byte *)(iVar12 + 3) != uVar2);
          iVar13 = *(int *)(iVar4 + 0xec);
          uVar14 = *(uint *)(iVar12 + 4);
        }
        *(uint *)(iVar15 * 4 + iVar13) = uVar14;
        uVar14 = (uint)*(byte *)(iVar5 + 0xe);
      }
LAB_00124014:
      iVar17 = iVar17 + 1;
      piVar8 = piVar8 + 1;
    } while (iVar17 < (int)uVar14);
  }
  iVar4 = FUN_001213d8(*(undefined4 *)(iVar16 + 4));
  if (*(byte *)(iVar4 + 0x12) == 0) {
    iRam0029079c = 0;
    FUN_001248a0(param_1,*(undefined4 *)(iVar16 + 4),auStack_50);
    piVar8 = (int *)FUN_0010d020(0x10);
    iVar5 = iRam0029079c;
    *(int **)(iVar16 + 0x70) = piVar8;
    *piVar8 = iVar5;
    if (iVar5 == 0) {
      piVar8[1] = 0;
      bVar3 = *(byte *)(iVar4 + 0x12);
    }
    else {
      uVar7 = FUN_0010d020(iVar5 << 2);
      iVar5 = iRam0029079c;
      *(int *)(*(int *)(iVar16 + 0x70) + 4) = (int)uVar7;
      FUN_0020c74c(uVar7,0x2cb790,iVar5 << 2);
      bVar3 = *(byte *)(iVar4 + 0x12);
    }
  }
  else {
    iVar5 = 0;
    uVar6 = FUN_0010d020((uint)*(byte *)(iVar4 + 0x12) << 4);
    *(undefined4 *)(iVar16 + 0x70) = uVar6;
    bVar3 = 0;
    if (*(char *)(iVar4 + 0x12) != '\0') {
      iVar17 = 0;
      do {
        iRam0029079c = 0;
        if ((*(uint *)(iVar4 + 0x14) & 0x80000000) == 0) {
          FUN_00125f90(*(int *)(iVar4 + 0x54) + iVar17);
          iVar10 = *(int *)(iVar16 + 0x70);
        }
        else {
          FUN_00126070(*(undefined4 *)(iVar5 * 4 + *(int *)(iVar4 + 0x54)));
          iVar10 = *(int *)(iVar16 + 0x70);
        }
        iVar15 = iVar5 * 0x10;
        iVar5 = iVar5 + 1;
        piVar8 = (int *)(iVar15 + iVar10);
        iVar10 = iRam0029079c << 2;
        bVar1 = iRam0029079c == 0;
        *piVar8 = iRam0029079c;
        if (bVar1) {
          piVar8[1] = 0;
          bVar3 = *(byte *)(iVar4 + 0x12);
        }
        else {
          uVar7 = FUN_0010d020(iVar10);
          iVar10 = iRam0029079c;
          *(int *)(iVar15 + *(int *)(iVar16 + 0x70) + 4) = (int)uVar7;
          FUN_0020c74c(uVar7,0x2cb790,iVar10 << 2);
          bVar3 = *(byte *)(iVar4 + 0x12);
        }
        iVar17 = iVar17 + 0x2c;
      } while (iVar5 < (int)(uint)bVar3);
      bVar3 = *(byte *)(iVar4 + 0x12);
    }
  }
  uVar14 = 1;
  if (1 < bVar3) {
    uVar14 = (uint)*(byte *)(iVar4 + 0x12);
  }
  if (uVar14 != 0) {
    iVar4 = 0;
    do {
      iVar5 = *(int *)(iVar16 + 0x70);
      iVar17 = 0;
      iVar10 = 0;
      piVar11 = (int *)(iVar4 + iVar5);
      piVar8 = aiStack_450;
      if (0 < *piVar11) {
        do {
          iVar13 = iVar17 * 4;
          iVar15 = **(int **)(iVar13 + *(int *)(iVar4 + iVar5 + 4));
          if (iVar15 != 0) {
            bVar1 = false;
            if (0 < iVar10) {
              if (iVar15 == aiStack_450[0]) {
                bVar1 = true;
              }
              else {
                for (iVar15 = 1; iVar15 < iVar10; iVar15 = iVar15 + 1) {
                  if (**(int **)(iVar13 + piVar11[1]) == aiStack_450[iVar15]) {
                    bVar1 = true;
                    break;
                  }
                }
              }
            }
            if (!bVar1) {
              iVar10 = iVar10 + 1;
              *piVar8 = **(undefined4 **)(iVar13 + piVar11[1]);
              piVar8 = piVar8 + 1;
            }
          }
          iVar17 = iVar17 + 1;
        } while (iVar17 < *(int *)(iVar4 + iVar5));
      }
      *(undefined4 *)(iVar4 + iVar5 + 0xc) = 0;
      *(int *)(iVar4 + iVar5 + 8) = iVar10;
      if (iVar10 != 0) {
        uVar7 = FUN_0010d020(iVar10 << 2);
        *(int *)(iVar4 + *(int *)(iVar16 + 0x70) + 0xc) = (int)uVar7;
        FUN_0020c74c(uVar7,aiStack_450,iVar10 << 2);
      }
      uVar14 = uVar14 - 1;
      iVar4 = iVar4 + 0x10;
    } while (uVar14 != 0);
  }
  FUN_001242e0(param_1);
  return;
}

