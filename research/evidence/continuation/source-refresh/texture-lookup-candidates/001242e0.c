
/* WARNING: Removing unreachable block (ram,0x00124370) */

void FUN_001242e0(undefined8 param_1)

{
  bool bVar1;
  byte bVar2;
  ushort uVar3;
  bool bVar4;
  int iVar5;
  int iVar6;
  undefined4 uVar7;
  undefined8 uVar8;
  int *piVar9;
  uint *puVar10;
  int iVar11;
  int *piVar12;
  int iVar13;
  int iVar14;
  uint uVar15;
  int iVar16;
  int iVar17;
  int iVar18;
  int aiStack_460 [256];
  undefined1 auStack_60 [16];
  
  iVar17 = (int)param_1;
  iVar5 = FUN_0021b6e0(*(undefined4 *)(iVar17 + 4));
  iVar6 = FUN_001213d8(*(undefined4 *)(iVar17 + 4));
  uVar3 = *(ushort *)(iVar17 + 100);
  uVar15 = (uint)*(byte *)(iVar6 + 0xe);
  iVar18 = 0;
  if (uVar15 != 0) {
    iVar11 = *(int *)(iVar5 + 0xf4);
    piVar9 = *(int **)(iVar6 + 0x1c);
    do {
      iVar16 = *piVar9;
      puVar10 = (uint *)(iVar16 * 8 + iVar11);
      if (((*puVar10 & 0x1000) != 0) && (*(char *)((int)puVar10 + 2) != '\0')) {
        iVar13 = 0;
        if (*(byte *)((int)puVar10 + 3) == uVar3) {
          iVar13 = *(int *)(iVar5 + 0xec);
          uVar15 = puVar10[1];
        }
        else {
          do {
            iVar13 = iVar13 + 1;
            iVar14 = (iVar16 + iVar13) * 8 + iVar11;
            if ((int)(uint)*(byte *)(iVar16 * 8 + iVar11 + 2) < iVar13) goto LAB_001243dc;
          } while (*(byte *)(iVar14 + 3) != uVar3);
          iVar13 = *(int *)(iVar5 + 0xec);
          uVar15 = *(uint *)(iVar14 + 4);
        }
        *(uint *)(iVar16 * 4 + iVar13) = uVar15;
        uVar15 = (uint)*(byte *)(iVar6 + 0xe);
      }
LAB_001243dc:
      iVar18 = iVar18 + 1;
      piVar9 = piVar9 + 1;
    } while (iVar18 < (int)uVar15);
  }
  iVar5 = FUN_001213d8(*(undefined4 *)(iVar17 + 4));
  if (*(byte *)(iVar5 + 0x12) == 0) {
    iRam0029079c = 0;
    FUN_00124a88(param_1,*(undefined4 *)(iVar17 + 4),auStack_60);
    if (iRam0029079c == 0) {
      iVar6 = *(int *)(iVar17 + 0x74);
      goto LAB_00124560;
    }
    piVar9 = (int *)FUN_0010d020(0x10);
    iVar6 = iRam0029079c;
    *(int **)(iVar17 + 0x74) = piVar9;
    *piVar9 = iVar6;
    if (iVar6 != 0) {
      uVar8 = FUN_0010d020(iVar6 << 2);
      iVar6 = iRam0029079c;
      *(int *)(*(int *)(iVar17 + 0x74) + 4) = (int)uVar8;
      FUN_0020c74c(uVar8,0x2cb790,iVar6 << 2);
      iVar6 = *(int *)(iVar17 + 0x74);
      goto LAB_00124560;
    }
    piVar9[1] = 0;
  }
  else {
    bVar4 = false;
    iVar6 = 0;
    uVar7 = FUN_0010d020((uint)*(byte *)(iVar5 + 0x12) << 4);
    *(undefined4 *)(iVar17 + 0x74) = uVar7;
    if (*(char *)(iVar5 + 0x12) != '\0') {
      iVar18 = 0;
      do {
        iRam0029079c = 0;
        if ((*(uint *)(iVar5 + 0x14) & 0x80000000) == 0) {
          FUN_00126000(*(int *)(iVar5 + 0x54) + iVar18);
          iVar11 = *(int *)(iVar17 + 0x74);
        }
        else {
          FUN_001261a0(*(undefined4 *)(iVar6 * 4 + *(int *)(iVar5 + 0x54)));
          iVar11 = *(int *)(iVar17 + 0x74);
        }
        iVar16 = iVar6 * 0x10;
        iVar6 = iVar6 + 1;
        piVar9 = (int *)(iVar16 + iVar11);
        iVar11 = iRam0029079c << 2;
        bVar1 = iRam0029079c == 0;
        *piVar9 = iRam0029079c;
        if (bVar1) {
          piVar9[1] = 0;
          bVar2 = *(byte *)(iVar5 + 0x12);
        }
        else {
          bVar4 = true;
          uVar8 = FUN_0010d020(iVar11);
          iVar11 = iRam0029079c;
          *(int *)(iVar16 + *(int *)(iVar17 + 0x74) + 4) = (int)uVar8;
          FUN_0020c74c(uVar8,0x2cb790,iVar11 << 2);
          bVar2 = *(byte *)(iVar5 + 0x12);
        }
        iVar18 = iVar18 + 0x2c;
      } while (iVar6 < (int)(uint)bVar2);
    }
    if (bVar4) {
      iVar6 = *(int *)(iVar17 + 0x74);
      goto LAB_00124560;
    }
    FUN_0010d100(*(undefined4 *)(iVar17 + 0x74));
    *(undefined4 *)(iVar17 + 0x74) = 0;
  }
  iVar6 = *(int *)(iVar17 + 0x74);
LAB_00124560:
  if (iVar6 != 0) {
    uVar15 = 1;
    if (1 < *(byte *)(iVar5 + 0x12)) {
      uVar15 = (uint)*(byte *)(iVar5 + 0x12);
    }
    iVar5 = 0;
    if (uVar15 != 0) {
      iVar18 = 0;
      do {
        iVar11 = 0;
        piVar12 = (int *)(iVar18 + iVar6);
        iVar16 = 0;
        piVar9 = aiStack_460;
        if (0 < *piVar12) {
          do {
            iVar14 = iVar11 * 4;
            iVar13 = **(int **)(iVar14 + *(int *)(iVar18 + iVar6 + 4));
            if (iVar13 != 0) {
              bVar4 = false;
              if (0 < iVar16) {
                if (iVar13 == aiStack_460[0]) {
                  bVar4 = true;
                }
                else {
                  for (iVar13 = 1; iVar13 < iVar16; iVar13 = iVar13 + 1) {
                    if (**(int **)(iVar14 + piVar12[1]) == aiStack_460[iVar13]) {
                      bVar4 = true;
                      break;
                    }
                  }
                }
              }
              if (!bVar4) {
                iVar16 = iVar16 + 1;
                *piVar9 = **(undefined4 **)(iVar14 + piVar12[1]);
                piVar9 = piVar9 + 1;
              }
            }
            iVar11 = iVar11 + 1;
          } while (iVar11 < *(int *)(iVar18 + iVar6));
        }
        *(undefined4 *)(iVar18 + iVar6 + 0xc) = 0;
        *(int *)(iVar18 + iVar6 + 8) = iVar16;
        if (iVar16 != 0) {
          uVar8 = FUN_0010d020(iVar16 << 2);
          *(int *)(iVar18 + *(int *)(iVar17 + 0x74) + 0xc) = (int)uVar8;
          FUN_0020c74c(uVar8,aiStack_460,iVar16 << 2);
        }
        iVar5 = iVar5 + 1;
        if ((int)uVar15 <= iVar5) {
          return;
        }
        iVar6 = *(int *)(iVar17 + 0x74);
        iVar18 = iVar5 * 0x10;
      } while( true );
    }
  }
  return;
}

