
/* WARNING: Removing unreachable block (ram,0x00124b28) */

undefined4 * FUN_00124a88(long param_1,undefined8 param_2,undefined4 *param_3)

{
  ushort uVar1;
  int iVar2;
  int iVar3;
  undefined4 *puVar4;
  int iVar5;
  int iVar6;
  uint *puVar7;
  int iVar8;
  int iVar9;
  uint uVar10;
  int *piVar11;
  int iVar12;
  
  uRam0029079c = 0;
  if (param_1 == 0) {
    puVar4 = (undefined4 *)FUN_001213d8(param_2);
  }
  else {
    iVar12 = (int)param_1;
    puVar4 = (undefined4 *)FUN_001213d8(*(undefined4 *)(iVar12 + 4));
    iVar5 = FUN_0021b6e0(*(undefined4 *)(iVar12 + 4));
    iVar6 = FUN_001213d8(*(undefined4 *)(iVar12 + 4));
    uVar1 = *(ushort *)(iVar12 + 100);
    uVar10 = (uint)*(byte *)(iVar6 + 0xe);
    iVar12 = 0;
    if (uVar10 != 0) {
      iVar2 = *(int *)(iVar5 + 0xf4);
      piVar11 = *(int **)(iVar6 + 0x1c);
      do {
        iVar3 = *piVar11;
        puVar7 = (uint *)(iVar3 * 8 + iVar2);
        if (((*puVar7 & 0x1000) != 0) && (*(char *)((int)puVar7 + 2) != '\0')) {
          iVar9 = 0;
          if (*(byte *)((int)puVar7 + 3) == uVar1) {
            iVar9 = *(int *)(iVar5 + 0xec);
            uVar10 = puVar7[1];
          }
          else {
            do {
              iVar9 = iVar9 + 1;
              iVar8 = (iVar3 + iVar9) * 8 + iVar2;
              if ((int)(uint)*(byte *)(iVar3 * 8 + iVar2 + 2) < iVar9) goto LAB_00124b94;
            } while (*(byte *)(iVar8 + 3) != uVar1);
            iVar9 = *(int *)(iVar5 + 0xec);
            uVar10 = *(uint *)(iVar8 + 4);
          }
          *(uint *)(iVar3 * 4 + iVar9) = uVar10;
          uVar10 = (uint)*(byte *)(iVar6 + 0xe);
        }
LAB_00124b94:
        iVar12 = iVar12 + 1;
        piVar11 = piVar11 + 1;
      } while (iVar12 < (int)uVar10);
      iVar5 = puVar4[5];
      goto LAB_00124bb8;
    }
  }
  iVar5 = puVar4[5];
LAB_00124bb8:
  if (iVar5 < 0) {
    iVar5 = 0;
    if (*(char *)((int)puVar4 + 0x11) != '\0') {
      iVar6 = puVar4[0x15];
      while( true ) {
        iVar12 = iVar5 * 4;
        iVar5 = iVar5 + 1;
        FUN_001261a0(*(undefined4 *)(iVar12 + iVar6));
        if ((int)(uint)*(byte *)((int)puVar4 + 0x11) <= iVar5) break;
        iVar6 = puVar4[0x15];
      }
    }
  }
  else {
    iVar5 = 0;
    FUN_001261a0(*puVar4);
    if (*(char *)((int)puVar4 + 0x11) != '\0') {
      iVar12 = 0;
      iVar6 = puVar4[0x15];
      while( true ) {
        iVar5 = iVar5 + 1;
        iVar6 = iVar6 + iVar12;
        iVar12 = iVar12 + 0x2c;
        FUN_00126000(iVar6);
        if ((int)(uint)*(byte *)((int)puVar4 + 0x11) <= iVar5) break;
        iVar6 = puVar4[0x15];
      }
    }
  }
  *param_3 = uRam0029079c;
  return &DAT_002cb790;
}

