class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.4/pim-manager_0.4.4_darwin_arm64.tar.gz"
      sha256 "2b0f15e526b6a62c62bd29f95de7ae745a52c336f0725a64cc3623e3ac2e03d1"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.4/pim-manager_0.4.4_darwin_amd64.tar.gz"
      sha256 "17255cf1f8fabb9993f195e47bb96cf91066fb64f7fa632eea438aa1fb79573f"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.4/pim-manager_0.4.4_linux_arm64.tar.gz"
      sha256 "dd340cb229e03dfdb1739abe1c48e95e4cabbfa27c79427c98a4e378db7dc8a3"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.4/pim-manager_0.4.4_linux_amd64.tar.gz"
      sha256 "f0677d835dd137b493db0ad8685539cd3a4dd681e4094ed76683e2fd849ea1b4"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
