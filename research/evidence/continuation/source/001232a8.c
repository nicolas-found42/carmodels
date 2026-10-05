
undefined4 FUN_001232a8(int param_1,int param_2)

{
  ushort uVar1;
  undefined4 *puVar2;
  undefined4 *puVar3;
  int iVar4;
  undefined4 uVar5;
  long lVar6;
  uint uVar7;
  int iVar8;
  int iVar9;
  int iVar10;
  uint *puVar11;
  int iVar12;
  undefined4 uVar13;
  int iStack_5c;
  
  iVar9 = *(int *)(param_2 + 8);
  puVar2 = *(undefined4 **)(param_1 + 4);
  for (puVar3 = (undefined4 *)**(undefined4 **)(param_1 + 4); puVar3 != (undefined4 *)0x0;
      puVar3 = (undefined4 *)*puVar3) {
    puVar2 = puVar3;
  }
  iVar12 = 0;
  iStack_5c = 0;
  iVar4 = FUN_001213d8(puVar2[1]);
  uVar5 = *(undefined4 *)(param_1 + 0x10);
  uVar7 = (uint)*(byte *)(iVar4 + 0x15);
  puVar11 = *(uint **)(iVar4 + 0x34);
  if (uVar7 == 0) {
LAB_001233dc:
    if (iVar12 == 0) {
      *(undefined4 *)(param_2 + 0x10) = 0;
      uVar5 = 2;
    }
    else {
      uVar5 = FUN_00123450(puVar2[1],iVar12,puVar2);
      *(int *)(param_2 + 0x10) = iVar12;
      uVar13 = *(undefined4 *)(iVar12 + 0x18);
      *(undefined4 *)(param_2 + 4) = uVar5;
      uVar5 = 1;
      *(undefined4 *)(param_2 + 0x14) = uVar13;
      *(undefined4 *)(param_2 + 0x18) = *(undefined4 *)(iVar12 + 0x1c);
      *(undefined4 *)(param_2 + 0x1c) = *(undefined4 *)(iVar12 + 0x20);
    }
    return uVar5;
  }
  uVar1 = *(ushort *)(param_2 + 0xc);
LAB_00123340:
  if (*puVar11 == (uint)uVar1) {
    iVar10 = 0;
    if (-1 < iVar9) {
      if (0 < (int)puVar11[1]) {
        uVar7 = puVar11[2];
        do {
          iVar8 = iVar10 * 4;
          iVar10 = iVar10 + 1;
          lVar6 = FUN_001238c8(uVar5,*(undefined4 *)(iVar8 + uVar7));
          if (lVar6 != 0) {
            iVar12 = *(int *)(iVar8 + puVar11[2]);
            if (iVar9 == 0) goto LAB_001233b4;
            iVar9 = iVar9 + -1;
          }
          if (iVar9 < 0) {
            uVar7 = (uint)*(byte *)(iVar4 + 0x15);
            goto LAB_001233b8;
          }
          if ((int)puVar11[1] <= iVar10) goto LAB_001233b4;
          uVar7 = puVar11[2];
        } while( true );
      }
      if (iVar9 != 0) {
        iVar12 = 0;
      }
      goto LAB_001233c0;
    }
    goto LAB_001233b8;
  }
  goto LAB_001233c0;
LAB_001233b4:
  uVar7 = (uint)*(byte *)(iVar4 + 0x15);
LAB_001233b8:
  if (iVar9 != 0) {
    iVar12 = 0;
  }
LAB_001233c0:
  iStack_5c = iStack_5c + 1;
  puVar11 = puVar11 + 3;
  if (((int)uVar7 <= iStack_5c) || (iVar12 != 0)) goto LAB_001233dc;
  uVar1 = *(ushort *)(param_2 + 0xc);
  goto LAB_00123340;
}

